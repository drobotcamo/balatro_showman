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
--   * objects cover the hand / pending selection / jokers / consumables only.
--     persistent_state and legal_actions are intentionally sparse for the
--     smoke test; this is not a canonical live/2.0.0 model-input snapshot.
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

local function current_page()
  local state = G and G.STATE
  if state == nil then return "Unknown" end
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

local function encode_state()
  local values = state_values()
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
    .. ',"modifier":null,"edition":null,"seal":null'
    .. ',"card":' .. encode_card_body(card, fields) .. "}"
end

local function encode_pending_card(card)
  local fields = card_fields(card)
  if not fields then return nil end
  return '{"class_id":' .. tostring(fields.class_id)
    .. ',"object_type":"card","modifier":null,"edition":null,"seal":null'
    .. ',"card":' .. encode_card_body(card, fields) .. "}"
end

local function center_key(card)
  local center = card.config and card.config.center
  return center and center.key or nil
end

local function encode_inventory_object(card, object_type, zone, position)
  local parts = {
    '"class_id":null',
    '"object_type":' .. j_str(object_type),
    '"zone":' .. j_str(zone),
    '"position_in_zone":' .. tostring(position),
    '"modifier":null,"edition":null,"seal":null',
    '"card":null',
  }
  local key = center_key(card)
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

  return objects, pending_cards
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
  local parts = {
    '"run_id":' .. j_str(run_id),
    '"game_state_id":' .. tostring(request_counter),
    '"game_stage_id":' .. tostring((G and G.STAGE) or 0),
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
  local parts = {
    '"schema_version":"live/2.0.0"',
    '"request_id":' .. tostring(rid),
    '"page_name":' .. j_str(page),
    '"source_kind":null',
    '"action_subtype":null',
    '"state":' .. encode_state(),
    '"objects":[' .. table.concat(objects, ",") .. "]",
    '"pending_cards":[' .. table.concat(pending_cards, ",") .. "]",
    '"target_zone":null',
    '"target_position":null',
    '"persistent_state":{}',
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
