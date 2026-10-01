-- balatro_showman_bridge main.lua
-- ==================================
-- Minimal Phase 0 Lua producer for the existing file-IPC oracle contract
-- (README: planning/BRIDGE_SPIKE.md). It observes the running game and writes:
--
--   %APPDATA%/Balatro/agent_io/snapshot.json   (state + action_taken + meta)
--   %APPDATA%/Balatro/agent_io/run_end.json    (run_id + outcome "win"|"loss")
--
-- consumed by ground_truth/file_ipc_bridge.py.
--
-- Scope (deliberately small, see Issue #6):
--   * Snapshot is written BEFORE the hooked action runs, so the captured state
--     is the decision state and action_taken is the player's real action.
--   * objects cover the hand / pending selection / jokers / consumables and
--     the shop and opened-pack offering zones (TopShelfShopOfferings,
--     VoucherShopOfferings, PackShopOfferings, PackOfferings).
--     Inventory objects carry the canonical `class_id` from the vendored class
--     map (unmapped keys stay null with `center_key` retained); every object
--     carries modifier/edition/seal (null when absent) and list-valued
--     stickers.
--   * raw_persistent carries the engine-truth raw persistent fields the
--     reducer needs (D021, Issue #21): deck, stake, deck flags, the full
--     playing-card deck with attributes, hand levels, vouchers, bosses, blind
--     statuses, and run counters. It is NOT canonical `persistent_state`
--     (state_schema.md §3); that shape stays owned by the pipeline reducer,
--     so `persistent_state` itself remains an empty object here.
--   * legal_actions / mask_basis carry the engine's own legality for the
--     coarse base actions (mask_schema.md §2-3) as the Phase 7 mask
--     validation reference. Shop/pack offering targets are Issue #16 and
--     canonical zoned labels are Issue #13; neither is attempted here.
--   * Every engine read is failure-isolated: an unavailable field is emitted
--     as null, never guessed.
--   * No game assets, saves, or logs are copied anywhere; only JSON state is
--     written to the shared agent_io directory.

local Bridge = {}

local function io_dir()
  local appdata = os.getenv("APPDATA")
  if appdata and appdata ~= "" then
    return appdata .. "\\Balatro\\agent_io"
  end
  local ok, dir = pcall(function() return love.filesystem.getSaveDirectory() end)
  if ok and dir and dir ~= "" then
    return dir .. "/agent_io"
  end
  return "agent_io"
end

local IO_DIR = io_dir()
local SNAPSHOT_PATH = IO_DIR .. "\\snapshot.json"
local RUN_END_PATH = IO_DIR .. "\\run_end.json"

local request_counter = 0
local run_id = nil
local run_finalized = false
local hooks_installed = false
local last_emit_clock = -math.huge

-- ---------------------------------------------------------------------------
-- JSON helpers (dependency-free; fixed shapes are built explicitly)
-- ---------------------------------------------------------------------------

local function j_str(value)
  local s = tostring(value)
  s = s:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
  s = s:gsub("\r", "\\r"):gsub("\t", "\\t")
  return '"' .. s .. '"'
end

local function j_num(value)
  local n = tonumber(value)
  if not n then return "0" end
  if n == math.floor(n) and math.abs(n) < 1e15 then
    return string.format("%d", n)
  end
  return string.format("%.6f", n)
end

local function j_scalar(value)
  local t = type(value)
  if value == nil then return "null" end
  if t == "boolean" then return tostring(value) end
  if t == "number" then return j_num(value) end
  return j_str(value)
end

-- Failure-isolated engine read: any error or unavailable field yields nil so
-- the encoder can emit explicit null instead of guessing.
local function try(fn)
  local ok, value = pcall(fn)
  if ok then return value end
  return nil
end

-- Sorted JSON object of a game table, recursing into nested tables up to
-- max_depth; every leaf is a scalar, an explicit null, or a nested object, so
-- engine values are never guessed or silently dropped. Depth-capped against
-- cyclic game tables.
local function table_json_value(value, max_depth, depth)
  if depth > max_depth then return "null" end
  local t = type(value)
  if t ~= "table" then return j_scalar(value) end
  local parts = {}
  local keys = {}
  for key in pairs(value) do keys[#keys + 1] = tostring(key) end
  table.sort(keys)
  for _, key in ipairs(keys) do
    local entry = try(function() return value[key] end)
    parts[#parts + 1] = j_str(key) .. ":" .. table_json_value(entry, max_depth, depth + 1)
  end
  return "{" .. table.concat(parts, ",") .. "}"
end

local function table_json(source, max_depth)
  return table_json_value(try(source), max_depth or 3, 0)
end

local function game_number_json(fn)
  local value = try(fn)
  if type(value) == "number" then return j_num(value) end
  return "null"
end

local function game_boolean_json(fn)
  local value = try(fn)
  if type(value) == "boolean" then return tostring(value) end
  return "null"
end

-- ---------------------------------------------------------------------------
-- Game state extraction
-- ---------------------------------------------------------------------------

local SUIT_INDEX = { Spades = 0, Hearts = 1, Diamonds = 2, Clubs = 3 }
local SUIT_NAME = { "Spades", "Hearts", "Diamonds", "Clubs" }
local RANK_INDEX = {
  Ace = 0, ["2"] = 1, ["3"] = 2, ["4"] = 3, ["5"] = 4, ["6"] = 5,
  ["7"] = 6, ["8"] = 7, ["9"] = 8, ["10"] = 9, Jack = 10, Queen = 11, King = 12,
}
local RANK_NAME = { "A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K" }

-- ---------------------------------------------------------------------------
-- Canonical ontology class IDs (D003: extend, never renumber)
--
-- The class names are exactly the game's `center_key` values for inventory
-- objects, so the table below maps `center_key` -> canonical `class_id` from
-- the vendored class map. Standard playing cards (class_id 0..51) are not in
-- this table: their class_id is computed from suit/rank. An unmapped
-- `center_key` yields a null `class_id` and is retained verbatim, never
-- guessed. Regenerate with `ground_truth/generate_class_ids.py`.
-- ---------------------------------------------------------------------------

-- BEGIN GENERATED CLASS ID TABLE
local CLASS_ID_BY_CENTER_KEY = {
  b_abandoned = 52,
  b_anaglyph = 53,
  b_black = 54,
  b_blue = 55,
  b_challenge = 56,
  b_checkered = 57,
  b_erratic = 58,
  b_ghost = 59,
  b_green = 60,
  b_magic = 61,
  b_nebula = 62,
  b_painted = 63,
  b_plasma = 64,
  b_red = 65,
  b_yellow = 66,
  b_zodiac = 67,
  e_foil = 68,
  e_holo = 69,
  e_negative = 70,
  e_polychrome = 71,
  m_bonus = 72,
  m_glass = 73,
  m_gold = 74,
  m_lucky = 75,
  m_mult = 76,
  m_steel = 77,
  m_stone = 78,
  m_wild = 79,
  j_8_ball = 80,
  j_abstract = 81,
  j_acrobat = 82,
  j_ancient = 83,
  j_arrowhead = 84,
  j_astronomer = 85,
  j_banner = 86,
  j_baron = 87,
  j_baseball = 88,
  j_blackboard = 89,
  j_bloodstone = 90,
  j_blue_joker = 91,
  j_blueprint = 92,
  j_bootstraps = 93,
  j_brainstorm = 94,
  j_bull = 95,
  j_burglar = 96,
  j_burnt = 97,
  j_business = 98,
  j_caino = 99,
  j_campfire = 100,
  j_card_sharp = 101,
  j_cartomancer = 102,
  j_castle = 103,
  j_cavendish = 104,
  j_ceremonial = 105,
  j_certificate = 106,
  j_chaos = 107,
  j_chicot = 108,
  j_clever = 109,
  j_cloud_9 = 110,
  j_constellation = 111,
  j_crafty = 112,
  j_crazy = 113,
  j_credit_card = 114,
  j_delayed_grat = 115,
  j_devious = 116,
  j_diet_cola = 117,
  j_dna = 118,
  j_drivers_license = 119,
  j_droll = 120,
  j_drunkard = 121,
  j_duo = 122,
  j_dusk = 123,
  j_egg = 124,
  j_erosion = 125,
  j_even_steven = 126,
  j_faceless = 127,
  j_family = 128,
  j_fibonacci = 129,
  j_flash = 130,
  j_flower_pot = 131,
  j_fortune_teller = 132,
  j_four_fingers = 133,
  j_gift = 134,
  j_glass = 135,
  j_gluttenous_joker = 136,
  j_golden = 137,
  j_greedy_joker = 138,
  j_green_joker = 139,
  j_gros_michel = 140,
  j_hack = 141,
  j_half = 142,
  j_hallucination = 143,
  j_hanging_chad = 144,
  j_hiker = 145,
  j_hit_the_road = 146,
  j_hologram = 147,
  j_ice_cream = 148,
  j_idol = 149,
  j_invisible = 150,
  j_joker = 151,
  j_jolly = 152,
  j_juggler = 153,
  j_loyalty_card = 154,
  j_luchador = 155,
  j_lucky_cat = 156,
  j_lusty_joker = 157,
  j_mad = 158,
  j_madness = 159,
  j_mail = 160,
  j_marble = 161,
  j_matador = 162,
  j_merry_andy = 163,
  j_midas_mask = 164,
  j_mime = 165,
  j_misprint = 166,
  j_mr_bones = 167,
  j_mystic_summit = 168,
  j_obelisk = 169,
  j_odd_todd = 170,
  j_onyx_agate = 171,
  j_oops = 172,
  j_order = 173,
  j_pareidolia = 174,
  j_perkeo = 175,
  j_photograph = 176,
  j_popcorn = 177,
  j_raised_fist = 178,
  j_ramen = 179,
  j_red_card = 180,
  j_reserved_parking = 181,
  j_ride_the_bus = 182,
  j_riff_raff = 183,
  j_ring_master = 184,
  j_rocket = 185,
  j_rough_gem = 186,
  j_runner = 187,
  j_satellite = 188,
  j_scary_face = 189,
  j_scholar = 190,
  j_seance = 191,
  j_seeing_double = 192,
  j_selzer = 193,
  j_shoot_the_moon = 194,
  j_shortcut = 195,
  j_sixth_sense = 196,
  j_sly = 197,
  j_smeared = 198,
  j_smiley = 199,
  j_sock_and_buskin = 200,
  j_space = 201,
  j_splash = 202,
  j_square = 203,
  j_steel_joker = 204,
  j_stencil = 205,
  j_stone = 206,
  j_stuntman = 207,
  j_supernova = 208,
  j_superposition = 209,
  j_swashbuckler = 210,
  j_throwback = 211,
  j_ticket = 212,
  j_to_the_moon = 213,
  j_todo_list = 214,
  j_trading = 215,
  j_tribe = 216,
  j_triboulet = 217,
  j_trio = 218,
  j_troubadour = 219,
  j_trousers = 220,
  j_turtle_bean = 221,
  j_vagabond = 222,
  j_vampire = 223,
  j_walkie_talkie = 224,
  j_wee = 225,
  j_wily = 226,
  j_wrathful_joker = 227,
  j_yorick = 228,
  j_zany = 229,
  debuffed = 230,
  facedown = 231,
  blue_seal = 232,
  gold_seal = 233,
  purple_seal = 234,
  red_seal = 235,
  c_ceres = 236,
  c_earth = 237,
  c_eris = 238,
  c_jupiter = 239,
  c_mars = 240,
  c_mercury = 241,
  c_neptune = 242,
  c_planet_x = 243,
  c_pluto = 244,
  c_saturn = 245,
  c_uranus = 246,
  c_venus = 247,
  c_ankh = 248,
  c_aura = 249,
  c_black_hole = 250,
  c_cryptid = 251,
  c_deja_vu = 252,
  c_ectoplasm = 253,
  c_familiar = 254,
  c_grim = 255,
  c_hex = 256,
  c_immolate = 257,
  c_incantation = 258,
  c_medium = 259,
  c_ouija = 260,
  c_sigil = 261,
  c_soul = 262,
  c_talisman = 263,
  c_trance = 264,
  c_wraith = 265,
  stake_black = 266,
  stake_blue = 267,
  stake_gold = 268,
  stake_green = 269,
  stake_orange = 270,
  stake_purple = 271,
  stake_red = 272,
  stake_white = 273,
  tag_boss = 274,
  tag_buffoon = 275,
  tag_charm = 276,
  tag_coupon = 277,
  tag_d_six = 278,
  tag_double = 279,
  tag_economy = 280,
  tag_ethereal = 281,
  tag_foil = 282,
  tag_garbage = 283,
  tag_handy = 284,
  tag_holo = 285,
  tag_investment = 286,
  tag_juggle = 287,
  tag_meteor = 288,
  tag_negative = 289,
  tag_orbital = 290,
  tag_polychrome = 291,
  tag_rare = 292,
  tag_skip = 293,
  tag_standard = 294,
  tag_top_up = 295,
  tag_uncommon = 296,
  tag_voucher = 297,
  c_chariot = 298,
  c_death = 299,
  c_devil = 300,
  c_emperor = 301,
  c_empress = 302,
  c_fool = 303,
  c_hanged_man = 304,
  c_heirophant = 305,
  c_hermit = 306,
  c_high_priestess = 307,
  c_judgement = 308,
  c_justice = 309,
  c_lovers = 310,
  c_magician = 311,
  c_moon = 312,
  c_star = 313,
  c_strength = 314,
  c_sun = 315,
  c_temperance = 316,
  c_tower = 317,
  c_wheel_of_fortune = 318,
  c_world = 319,
  v_antimatter = 320,
  v_blank = 321,
  v_clearance_sale = 322,
  v_crystal_ball = 323,
  v_directors_cut = 324,
  v_glow_up = 325,
  v_grabber = 326,
  v_hieroglyph = 327,
  v_hone = 328,
  v_illusion = 329,
  v_liquidation = 330,
  v_magic_trick = 331,
  v_money_tree = 332,
  v_nacho_tong = 333,
  v_observatory = 334,
  v_omen_globe = 335,
  v_overstock_norm = 336,
  v_overstock_plus = 337,
  v_paint_brush = 338,
  v_palette = 339,
  v_petroglyph = 340,
  v_planet_merchant = 341,
  v_planet_tycoon = 342,
  v_recyclomancy = 343,
  v_reroll_glut = 344,
  v_reroll_surplus = 345,
  v_retcon = 346,
  v_seed_money = 347,
  v_tarot_merchant = 348,
  v_tarot_tycoon = 349,
  v_telescope = 350,
  v_wasteful = 351,
  p_arcana_jumbo = 352,
  p_arcana_mega = 353,
  p_arcana_normal = 354,
  p_buffoon_jumbo = 355,
  p_buffoon_mega = 356,
  p_buffoon_normal = 357,
  p_celestial_jumbo = 358,
  p_celestial_mega = 359,
  p_celestial_normal = 360,
  p_spectral_jumbo = 361,
  p_spectral_mega = 362,
  p_spectral_normal = 363,
  p_standard_jumbo = 364,
  p_standard_mega = 365,
  p_standard_normal = 366,
  rental = 367,
  perishable = 368,
  eternal = 369,
  bl_arm = 370,
  bl_big = 371,
  bl_club = 372,
  bl_eye = 373,
  bl_final_acorn = 374,
  bl_final_bell = 375,
  bl_final_heart = 376,
  bl_final_leaf = 377,
  bl_final_vessel = 378,
  bl_fish = 379,
  bl_flint = 380,
  bl_goad = 381,
  bl_head = 382,
  bl_hook = 383,
  bl_house = 384,
  bl_manacle = 385,
  bl_mark = 386,
  bl_mouth = 387,
  bl_needle = 388,
  bl_ox = 389,
  bl_pillar = 390,
  bl_plant = 391,
  bl_psychic = 392,
  bl_serpent = 393,
  bl_small = 394,
  bl_tooth = 395,
  bl_wall = 396,
  bl_water = 397,
  bl_wheel = 398,
  bl_window = 399,
}
-- END GENERATED CLASS ID TABLE

-- Composition labels are attached to their parent object (D004), not folded
-- into the base `class_id`. Values are the vendored class names.
local EDITION_BY_TYPE = {
  foil = "e_foil",
  holo = "e_holo",
  polychrome = "e_polychrome",
  negative = "e_negative",
}
local SEAL_BY_NAME = {
  Red = "red_seal",
  Blue = "blue_seal",
  Gold = "gold_seal",
  Purple = "purple_seal",
}

local PAGE_BY_STATE = {
  [7] = "Blind_Select",
  [1] = "In_Blind",
  [2] = "In_Blind",
  [3] = "In_Blind",
  [5] = "In_Shop",
  [8] = "Cash_Out",
  [9] = "In_TarotSpectral_Pack",
  [15] = "In_TarotSpectral_Pack",
  [10] = "In_JokerStandardPlanet_Pack",
  [17] = "In_JokerStandardPlanet_Pack",
  [18] = "In_JokerStandardPlanet_Pack",
  [4] = "Game_Over",
}

-- Steamodded re-implements the booster UI and patches G.STATES itself:
--   SMODS_BOOSTER_OPENED = 999, SMODS_REDEEM_VOUCHER = 998
-- (smods-main/lovely/booster.toml). Pack kind distinguishes the two pack pages.
local function opened_booster_field(field)
  local ok, value = pcall(function()
    local booster = SMODS and SMODS.OPENED_BOOSTER
    local center = booster and booster.config and booster.config.center
    return center and center[field] or nil
  end)
  if ok then return value end
  return nil
end

local function pack_kind()
  return opened_booster_field("kind")
end

local function pack_key()
  return opened_booster_field("key")
end

local function current_page()
  local state = G and G.STATE
  if state == nil then return "Unknown" end
  if state == 999 then
    local kind = pack_kind()
    if kind == "Arcana" or kind == "Spectral" then return "In_TarotSpectral_Pack" end
    if kind == "Celestial" or kind == "Standard" or kind == "Buffoon" then
      return "In_JokerStandardPlanet_Pack"
    end
    return "Unknown_PackKind_" .. tostring(kind)
  end
  if state == 998 then return "In_Shop" end
  return PAGE_BY_STATE[state] or ("Unknown_" .. tostring(state))
end

local STATE_KEYS = {
  "hands_left", "discards_left", "dollars", "ante", "round",
  "deck_remaining", "deck_total", "round_score",
  "hand_size_current", "hand_size_total",
  "jokers_current", "jokers_total",
  "consumables_current", "consumables_total",
}

local function state_values()
  local game = (G and G.GAME) or {}
  local round = game.current_round or {}
  local resets = game.round_resets or {}
  return {
    hands_left = round.hands_left or 0,
    discards_left = round.discards_left or 0,
    dollars = game.dollars or 0,
    ante = resets.ante or 0,
    round = game.round or 0,
    deck_remaining = (G and G.deck and #G.deck.cards) or 0,
    deck_total = game.starting_deck_size or 52,
    round_score = game.chips or 0,
    hand_size_current = (G and G.hand and #G.hand.cards) or 0,
    hand_size_total = (G and G.hand and G.hand.config and G.hand.config.card_limit) or 8,
    jokers_current = (G and G.jokers and #G.jokers.cards) or 0,
    jokers_total = (G and G.jokers and G.jokers.config and G.jokers.config.card_limit) or 5,
    consumables_current = (G and G.consumeables and #G.consumeables.cards) or 0,
    consumables_total = (G and G.consumeables and G.consumeables.config and G.consumeables.config.card_limit) or 2,
  }
end

local function encode_state(values)
  local parts = {}
  for _, key in ipairs(STATE_KEYS) do
    parts[#parts + 1] = j_str(key) .. ":" .. j_scalar(values[key])
  end
  return "{" .. table.concat(parts, ",") .. "}"
end

local function card_fields(card)
  local suit_index = card.base and SUIT_INDEX[card.base.suit] or nil
  local rank_index = card.base and RANK_INDEX[card.base.value] or nil
  if suit_index == nil or rank_index == nil then return nil end
  return {
    class_id = suit_index * 13 + rank_index,
    suit_index = suit_index,
    rank_index = rank_index,
  }
end

local function j_str_array(values)
  local parts = {}
  for _, value in ipairs(values) do parts[#parts + 1] = j_str(value) end
  return "[" .. table.concat(parts, ",") .. "]"
end

local function center_key(card)
  local center = card.config and card.config.center
  return center and center.key or nil
end

local function class_id_for_center_key(key)
  if type(key) ~= "string" then return nil end
  return CLASS_ID_BY_CENTER_KEY[key]
end

-- Enhancement (m_*) is the playing card's active center; a normal card's center
-- is `c_base`. Only m_* centers are enhancement modifiers.
local function card_modifier(card)
  local key = center_key(card)
  if type(key) == "string" and key:sub(1, 2) == "m_" then return key end
  return nil
end

-- `card.edition.type` is the canonical key; fall back to the boolean flags.
local function card_edition(card)
  local edition = card.edition
  if type(edition) ~= "table" then return nil end
  local by_type = EDITION_BY_TYPE[edition.type]
  if by_type then return by_type end
  if edition.negative then return EDITION_BY_TYPE.negative end
  if edition.polychrome then return EDITION_BY_TYPE.polychrome end
  if edition.holo then return EDITION_BY_TYPE.holo end
  if edition.foil then return EDITION_BY_TYPE.foil end
  return nil
end

-- `card.seal` is the raw game name (Red/Blue/Gold/Purple).
local function card_seal(card)
  return SEAL_BY_NAME[card.seal]
end

-- Stickers are list-valued in the adopted contract (empty list when none).
local function card_stickers(card)
  local ability = card.ability
  if type(ability) ~= "table" then return {} end
  local stickers = {}
  if ability.rental then stickers[#stickers + 1] = "rental" end
  if ability.perishable then stickers[#stickers + 1] = "perishable" end
  if ability.eternal then stickers[#stickers + 1] = "eternal" end
  return stickers
end

-- modifier/edition/seal are null when absent (str | None in the contract).
local function card_attributes_json(card)
  local modifier = card_modifier(card)
  local edition = card_edition(card)
  local seal = card_seal(card)
  return '"modifier":' .. (modifier and j_str(modifier) or "null")
    .. ',"edition":' .. (edition and j_str(edition) or "null")
    .. ',"seal":' .. (seal and j_str(seal) or "null")
    .. ',"stickers":' .. j_str_array(card_stickers(card))
end

local function encode_card_body(card, fields)
  return '{"rank":' .. j_str(RANK_NAME[fields.rank_index + 1])
    .. ',"rank_index":' .. tostring(fields.rank_index)
    .. ',"suit":' .. j_str(SUIT_NAME[fields.suit_index + 1])
    .. ',"suit_index":' .. tostring(fields.suit_index)
    .. ',"is_ace":' .. tostring(fields.rank_index == 0)
    .. ',"is_face":' .. tostring(fields.rank_index >= 10) .. "}"
end

local function encode_playing_object(card, zone, position)
  local fields = card_fields(card)
  if not fields then return nil end
  return '{"class_id":' .. tostring(fields.class_id)
    .. ',"object_type":"card","zone":' .. j_str(zone)
    .. ',"position_in_zone":' .. tostring(position)
    .. ',' .. card_attributes_json(card)
    .. ',"card":' .. encode_card_body(card, fields) .. "}"
end

local function encode_pending_card(card)
  local fields = card_fields(card)
  if not fields then return nil end
  return '{"class_id":' .. tostring(fields.class_id)
    .. ',"object_type":"card",' .. card_attributes_json(card)
    .. ',"card":' .. encode_card_body(card, fields) .. "}"
end

local function encode_inventory_object(card, object_type, zone, position)
  local key = center_key(card)
  local class_id = class_id_for_center_key(key)
  local parts = {
    '"class_id":' .. (class_id and tostring(class_id) or "null"),
    '"object_type":' .. j_str(object_type),
    '"zone":' .. j_str(zone),
    '"position_in_zone":' .. tostring(position),
    card_attributes_json(card),
    '"card":null',
  }
  if key then parts[#parts + 1] = '"center_key":' .. j_str(key) end
  return "{" .. table.concat(parts, ",") .. "}"
end

local function consumable_type(card)
  local set = card.ability and card.ability.set
  if set == "Tarot" then return "tarot" end
  if set == "Planet" then return "planet" end
  if set == "Spectral" then return "spectral" end
  return "consumable"
end

-- Inventory type from the card's ability set, covering the shop and pack
-- offering families. Falls back to the generic consumable type used by the
-- existing consumables zone.
local function inventory_type(card)
  local set = card.ability and card.ability.set
  if set == "Joker" then return "joker" end
  if set == "Voucher" then return "voucher" end
  if set == "Booster" then return "pack" end
  if set == "Tarot" then return "tarot" end
  if set == "Planet" then return "planet" end
  if set == "Spectral" then return "spectral" end
  return "consumable"
end

-- Offering objects can be playing cards (e.g. Standard pack contents) or
-- inventory objects (jokers / consumables / vouchers / packs). Unmapped
-- `center_key`s keep `class_id:null`, per the adopted object schema.
local function encode_offer_object(card, zone, position)
  local fields = card_fields(card)
  if fields then return encode_playing_object(card, zone, position) end
  return encode_inventory_object(card, inventory_type(card), zone, position)
end

-- Append every card of a shop/pack CardArea to `objects`, ordered by
-- `position_in_zone`. An absent or empty area emits nothing.
local function append_offerings(objects, area, zone)
  if not (area and area.cards) then return end
  for i, card in ipairs(area.cards) do
    local object = encode_offer_object(card, zone, i - 1)
    if object then objects[#objects + 1] = object end
  end
end

local function build_objects()
  local objects = {}
  local pending_cards = {}

  if G and G.hand and G.hand.cards then
    for _, card in ipairs(G.hand.cards) do
      if card.highlighted then
        local pending = encode_pending_card(card)
        local pending_object = encode_playing_object(card, "PendingCards", #pending_cards)
        if pending then pending_cards[#pending_cards + 1] = pending end
        if pending_object then objects[#objects + 1] = pending_object end
      end
    end
    local hand_position = 0
    for _, card in ipairs(G.hand.cards) do
      if not card.highlighted then
        local object = encode_playing_object(card, "CurrentHand", hand_position)
        if object then
          objects[#objects + 1] = object
          hand_position = hand_position + 1
        end
      end
    end
  end

  if G and G.jokers and G.jokers.cards then
    for i, card in ipairs(G.jokers.cards) do
      objects[#objects + 1] = encode_inventory_object(card, "joker", "CurrentJokers", i - 1)
    end
  end

  if G and G.consumeables and G.consumeables.cards then
    for i, card in ipairs(G.consumeables.cards) do
      objects[#objects + 1] = encode_inventory_object(card, consumable_type(card), "CurrentConsumables", i - 1)
    end
  end

  -- Shop and opened-pack offering zones (D009 live/2.0 zone vocabulary):
  --   G.shop_jokers   -> TopShelfShopOfferings (jokers/consumables for sale)
  --   G.shop_vouchers -> VoucherShopOfferings
  --   G.shop_booster  -> PackShopOfferings (booster packs for sale)
  --   G.pack_cards    -> PackOfferings (contents of an opened booster)
  -- Bare `ShopOfferings` is a deprecated offline-extractor alias with no
  -- distinct live area, so it is intentionally not emitted (Issue #16).
  append_offerings(objects, G and G.shop_jokers, "TopShelfShopOfferings")
  append_offerings(objects, G and G.shop_vouchers, "VoucherShopOfferings")
  append_offerings(objects, G and G.shop_booster, "PackShopOfferings")
  append_offerings(objects, G and G.pack_cards, "PackOfferings")

  return objects, pending_cards
end

-- ---------------------------------------------------------------------------
-- Raw persistent fields (D021, Issue #21) — engine truth for the reducer
-- ---------------------------------------------------------------------------

local function deck_info()
  -- Steamodded reads the deck center at G.GAME.selected_back.effect.center.key
  -- (overrides.lua:2401); `selected_back_key` is the vanilla fallback.
  local key = try(function() return G.GAME.selected_back.effect.center.key end)
  if type(key) ~= "string" then
    key = try(function() return G.GAME.selected_back_key end)
  end
  if type(key) ~= "string" then
    return { center_key = nil, class_id = nil }
  end
  return { center_key = key, class_id = class_id_for_center_key(key) }
end

-- The stake's numeric level resolves through the engine's own stake pool
-- (SMODS.stake_from_index maps G.GAME.stake to G.P_CENTER_POOLS.Stake[level].
-- key); the stake_level scan over G.P_CENTERS is the fallback. Ties are
-- broken deterministically by sorting the matching keys.
local function stake_info()
  local level = try(function() return G.GAME.stake end)
  if type(level) ~= "number" then
    return { level = nil, center_key = nil }
  end
  local key = try(function()
    local center = G.P_CENTER_POOLS and G.P_CENTER_POOLS.Stake and G.P_CENTER_POOLS.Stake[level]
    return center and center.key or nil
  end)
  if type(key) ~= "string" then
    key = try(function()
      local matches = {}
      for center_key, center in pairs(G.P_CENTERS) do
        if type(center) == "table" and center.set == "Stake" and center.stake_level == level then
          matches[#matches + 1] = tostring(center_key)
        end
      end
      table.sort(matches)
      return matches[1]
    end)
  end
  if type(key) ~= "string" then key = nil end
  return { level = level, center_key = key }
end

-- G.playing_cards is the run's full playing-card list (cards leave G.deck as
-- they are drawn), so it is the raw basis for tracked_deck_cards; the
-- reducer owns the FIFO cap and canonical shaping.
local function tracked_deck_cards()
  local cards = try(function() return G.playing_cards end)
  local out = {}
  if type(cards) ~= "table" then return out end
  for _, card in ipairs(cards) do
    local fields = card_fields(card)
    if fields then
      out[#out + 1] = '{"class_id":' .. tostring(fields.class_id)
        .. ',"object_type":"card",' .. card_attributes_json(card)
        .. ',"card":' .. encode_card_body(card, fields) .. "}"
    end
  end
  return out
end

local function hand_levels_json()
  local hands = try(function() return G.GAME.hands end)
  local parts = {}
  if type(hands) == "table" then
    local names = {}
    for name in pairs(hands) do names[#names + 1] = tostring(name) end
    table.sort(names)
    for _, name in ipairs(names) do
      local hand = hands[name]
      parts[#parts + 1] = j_str(name) .. ":{"
        .. '"level":' .. game_number_json(function() return hand.level end)
        .. ',"played":' .. game_number_json(function() return hand.played end)
        .. ',"played_this_round":' .. game_number_json(function() return hand.played_this_round end)
        .. "}"
    end
  end
  return "{" .. table.concat(parts, ",") .. "}"
end

local function voucher_keys()
  local used = try(function() return G.GAME.used_vouchers end)
  local keys = {}
  if type(used) == "table" then
    for key, redeemed in pairs(used) do
      if redeemed then keys[#keys + 1] = tostring(key) end
    end
    table.sort(keys)
  end
  return keys
end

-- bosses_used is emitted verbatim; this runtime nests it as
-- {boss/small/big: {blind_key: count}} (SMODS.normalize_bosses_used_table),
-- and the reducer derives the canonical class-id list.
local function bosses_used_json()
  return table_json(function() return G.GAME.bosses_used end, 2)
end

local function encode_raw_persistent()
  local deck = deck_info()
  local stake = stake_info()
  local last_planet = try(function() return G.GAME.last_tarot_planet end)
  if type(last_planet) ~= "string" then last_planet = nil end
  local parts = {
    '"deck":{"center_key":' .. (deck.center_key and j_str(deck.center_key) or "null")
      .. ',"class_id":' .. (deck.class_id and tostring(deck.class_id) or "null") .. "}",
    '"stake":{"level":' .. (stake.level and j_num(stake.level) or "null")
      .. ',"center_key":' .. (stake.center_key and j_str(stake.center_key) or "null") .. "}",
    '"starting_params_no_faces":' .. game_boolean_json(function() return G.GAME.starting_params.no_faces end),
    '"modifiers":' .. table_json(function() return G.GAME.modifiers end),
    '"tracked_deck_cards":[' .. table.concat(tracked_deck_cards(), ",") .. "]",
    '"hand_levels":' .. hand_levels_json(),
    '"vouchers_redeemed":' .. j_str_array(voucher_keys()),
    '"bosses_used":' .. bosses_used_json(),
    '"blind_states":' .. table_json(function() return G.GAME.round_resets.blind_states end),
    '"blind_choices":' .. table_json(function() return G.GAME.round_resets.blind_choices end),
    '"blind_tags":' .. table_json(function() return G.GAME.round_resets.blind_tags end),
    '"boss_rerolled":' .. game_boolean_json(function() return G.GAME.round_resets.boss_rerolled end),
    '"skips":' .. game_number_json(function() return G.GAME.skips end),
    '"hands_played":' .. game_number_json(function() return G.GAME.hands_played end),
    '"unused_discards":' .. game_number_json(function() return G.GAME.unused_discards end),
    '"ecto_minus":' .. game_number_json(function() return G.GAME.ecto_minus end),
    '"last_tarot_planet":' .. (last_planet and j_str(last_planet) or "null"),
  }
  return "{" .. table.concat(parts, ",") .. "}"
end

-- ---------------------------------------------------------------------------
-- Engine legal actions / mask basis (mask_schema.md §2-3)
-- ---------------------------------------------------------------------------

local PACK_PAGES = {
  In_TarotSpectral_Pack = true,
  In_JokerStandardPlanet_Pack = true,
}

local function highlighted_count(area)
  local cards = try(function() return area.cards end)
  local count = 0
  if type(cards) == "table" then
    for _, card in ipairs(cards) do
      if try(function() return card.highlighted end) then count = count + 1 end
    end
  end
  return count
end

-- Sellable = highlighted owned joker/consumable without the eternal sticker
-- (mask_schema.md §3). Playing cards cannot be sold.
local function sellable_highlighted_count()
  local count = 0
  for _, area_name in ipairs({ "jokers", "consumeables" }) do
    local cards = try(function() return G[area_name].cards end)
    if type(cards) == "table" then
      for _, card in ipairs(cards) do
        local highlighted = try(function() return card.highlighted end)
        local eternal = try(function() return card.ability.eternal end)
        if highlighted and not eternal then count = count + 1 end
      end
    end
  end
  return count
end

local function encode_mask_basis(basis)
  local parts = {
    '"reroll_cost":' .. game_number_json(function() return G.GAME.current_round.reroll_cost end),
    '"free_rerolls":' .. game_number_json(function() return G.GAME.current_round.free_rerolls end),
    '"selected_hand_count":' .. tostring(basis.selected_hand),
    '"selected_consumable_count":' .. tostring(basis.selected_consumables),
    '"selected_sellable_count":' .. tostring(basis.sellable_selected),
  }
  return "{" .. table.concat(parts, ",") .. "}"
end

-- Coarse base-action legality for the snapshot's decision state. Page gating
-- follows mask_schema.md §2; the availability facts are §3. Items that need
-- shop/pack offering contents (per-item BuyShopItem costs, SelectPackItem,
-- SelectCard) are Issue #16/#13 and are not emitted here. When a §3 fact is
-- unreadable its gating degrades to the §2 page gate and the null fact is
-- visible in mask_basis. The action about to run is always included: the
-- engine allowed it, and the client validates action_taken against this list.
local function compute_legal_actions(page, action_taken, values, basis)
  local legal = {}
  local function add(label) legal[label] = true end

  local blind_states = try(function() return G.GAME.round_resets.blind_states end)
  local blind_tags = try(function() return G.GAME.round_resets.blind_tags end)

  if page == "Blind_Select" then
    add("SelectBlind")
    for _, blind_name in ipairs({ "Small", "Big" }) do
      local selectable = type(blind_states) == "table" and blind_states[blind_name] == "Select"
      local offered_tag = type(blind_tags) == "table" and blind_tags[blind_name]
      if selectable and offered_tag then add("SkipBlind") end
    end
  elseif page == "In_Blind" then
    if basis.selected_hand > 0 then
      if (values.hands_left or 0) > 0 then add("PlayHand") end
      if (values.discards_left or 0) > 0 then add("DiscardHand") end
    end
  elseif page == "Cash_Out" then
    add("CashOut")
  elseif page == "In_Shop" then
    add("BuyShopItem")
    add("LeaveShop")
    local cost = try(function() return G.GAME.current_round.reroll_cost end)
    local free_rerolls = try(function() return G.GAME.current_round.free_rerolls end)
    if cost == nil or (type(free_rerolls) == "number" and free_rerolls > 0)
      or (type(values.dollars) == "number" and values.dollars >= cost) then
      add("RerollShop")
    end
  elseif PACK_PAGES[page] then
    add("SkipPack")
  end
  if basis.selected_consumables > 0 then add("UseConsumable") end
  if basis.sellable_selected > 0 then add("SellItem") end
  if action_taken then add(action_taken) end

  local list = {}
  for label in pairs(legal) do list[#list + 1] = label end
  table.sort(list)
  return list
end

-- ---------------------------------------------------------------------------
-- Runtime metadata
-- ---------------------------------------------------------------------------

local function steamodded_version()
  local ok, value = pcall(function()
    return SMODS and SMODS.Mods and SMODS.Mods["Steamodded"] and SMODS.Mods["Steamodded"].version
  end)
  if ok and value then return value end
  return "unknown"
end

local function lovely_version()
  local ok, lovely = pcall(require, "lovely")
  if ok and type(lovely) == "table" and lovely.version then return lovely.version end
  return "unknown"
end

local function encode_meta(page)
  local runtime = '{"balatro":' .. j_str((G and G.VERSION) or "unknown")
    .. ',"steamodded":' .. j_str(steamodded_version())
    .. ',"lovely":' .. j_str(lovely_version()) .. "}"
  local kind = nil
  local key = nil
  if G and G.STATE == 999 then
    kind = pack_kind()
    key = pack_key()
  end
  local parts = {
    '"run_id":' .. j_str(run_id),
    '"game_state_id":' .. tostring(request_counter),
    '"game_stage_id":' .. tostring((G and G.STAGE) or 0),
    '"game_state":' .. j_num((G and G.STATE) or -1),
    '"pack_kind":' .. (kind and j_str(kind) or "null"),
    '"pack_key":' .. (key and j_str(key) or "null"),
    '"sent_at_real_time":' .. j_num(os.time()),
    '"producer":"balatro_showman_bridge"',
    '"smoke_subset":true',
    '"page":' .. j_str(page),
    '"runtime":' .. runtime,
  }
  return "{" .. table.concat(parts, ",") .. "}"
end

-- ---------------------------------------------------------------------------
-- File IPC
-- ---------------------------------------------------------------------------

local function write_atomic(path, text)
  local tmp = path .. ".tmp"
  local handle = io.open(tmp, "wb")
  if not handle then return false end
  handle:write(text)
  handle:close()
  os.remove(path)
  local renamed = os.rename(tmp, path)
  if renamed then return true end
  local fallback = io.open(path, "wb")
  if fallback then
    fallback:write(text)
    fallback:close()
    os.remove(tmp)
    return true
  end
  os.remove(tmp)
  return false
end

local function build_snapshot(rid, page, action_label)
  local objects, pending_cards = build_objects()
  local values = state_values()
  local basis = {
    selected_hand = highlighted_count(G.hand),
    selected_consumables = highlighted_count(G.consumeables),
    sellable_selected = sellable_highlighted_count(),
  }
  local legal_actions = compute_legal_actions(page, action_label, values, basis)
  local parts = {
    '"schema_version":"live/3.0.0"',
    '"request_id":' .. tostring(rid),
    '"page_name":' .. j_str(page),
    '"source_kind":null',
    '"action_subtype":null',
    '"state":' .. encode_state(values),
    '"objects":[' .. table.concat(objects, ",") .. "]",
    '"pending_cards":[' .. table.concat(pending_cards, ",") .. "]",
    '"target_zone":null',
    '"target_position":null',
    '"persistent_state":{}',
    '"raw_persistent":' .. encode_raw_persistent(),
    '"legal_actions":' .. j_str_array(legal_actions),
    '"mask_basis":' .. encode_mask_basis(basis),
    '"action_taken":' .. j_str(action_label),
    '"meta":' .. encode_meta(page),
  }
  return "{" .. table.concat(parts, ",") .. "}"
end

function Bridge.emit(action_label)
  if not (G and G.STAGE == G.STAGES.RUN) then return end
  if not run_id then
    run_id = tostring(os.time()) .. "-" .. tostring(math.random(1000, 9999))
    run_finalized = false
  end
  -- Coalesce actions that fire back-to-back (e.g. buy_from_shop -> use_card)
  -- so a later write cannot overwrite a snapshot the Python client has not
  -- consumed yet. The first action in the pair is the meaningful one.
  local now = os.clock()
  if now - last_emit_clock < 0.03 then return end
  last_emit_clock = now
  request_counter = request_counter + 1
  local page = current_page()
  local wrote = write_atomic(SNAPSHOT_PATH, build_snapshot(request_counter, page, action_label))
  if not wrote then
    print("[balatro_showman_bridge] could not write " .. SNAPSHOT_PATH)
  end
end

local function finalize(outcome)
  if run_finalized or not run_id then return end
  run_finalized = true
  local body = '{"run_id":' .. j_str(run_id) .. ',"outcome":' .. j_str(outcome) .. "}"
  if not write_atomic(RUN_END_PATH, body) then
    print("[balatro_showman_bridge] could not write " .. RUN_END_PATH)
  end
end

-- ---------------------------------------------------------------------------
-- Hooks
-- ---------------------------------------------------------------------------

local ACTION_HOOKS = {
  play_cards_from_highlighted = "PlayHand",
  discard_cards_from_highlighted = "DiscardHand",
  select_blind = "SelectBlind",
  skip_blind = "SkipBlind",
  cash_out = "CashOut",
  reroll_shop = "RerollShop",
  buy_from_shop = "BuyShopItem",
  sell_card = "SellItem",
  use_card = "UseConsumable",
  skip_booster = "SkipPack",
  toggle_shop = "LeaveShop",
}

local function install_action_hooks()
  if hooks_installed or not G or not G.FUNCS then return end
  local wrapped = false
  for name, label in pairs(ACTION_HOOKS) do
    local original = G.FUNCS[name]
    if type(original) == "function" then
      wrapped = true
      G.FUNCS[name] = function(...)
        pcall(Bridge.emit, label)
        return original(...)
      end
    end
  end
  if wrapped then
    hooks_installed = true
    print("[balatro_showman_bridge] action hooks installed")
  end
end

function Bridge.tick()
  install_action_hooks()
  if run_id and not run_finalized and G and G.STATE == G.STATES.GAME_OVER then
    finalize((G.GAME and G.GAME.won) and "win" or "loss")
  end
end

local function install_game_hooks()
  if type(Game) ~= "table" then return end

  local original_update = Game.update
  if type(original_update) == "function" then
    Game.update = function(self, dt)
      original_update(self, dt)
      Bridge.tick()
    end
  end

  local original_start_run = Game.start_run
  if type(original_start_run) == "function" then
    Game.start_run = function(self, ...)
      run_id = tostring(os.time()) .. "-" .. tostring(math.random(1000, 9999))
      run_finalized = false
      return original_start_run(self, ...)
    end
  end

  local original_win_game = win_game
  if type(original_win_game) == "function" then
    win_game = function(...)
      finalize("win")
      return original_win_game(...)
    end
  end
end

-- ---------------------------------------------------------------------------
-- Boot
-- ---------------------------------------------------------------------------

pcall(function() love.filesystem.createDirectory("agent_io") end)
install_game_hooks()
install_action_hooks()

print("[balatro_showman_bridge] loaded; io_dir=" .. IO_DIR)

return Bridge
