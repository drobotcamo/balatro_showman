local function fail(message)
  io.stderr:write("producer queue fixture failed: " .. message .. "\n")
  love.event.quit(1)
end

function love.errorhandler(message)
  local trace = debug.traceback(tostring(message), 2)
  return function()
    io.stderr:write("producer fixture exception: " .. trace .. "\n")
    love.event.quit(1)
    return trace
  end
end

function love.load()
  local source = love.filesystem.getSourceBaseDirectory()
  local root = source:gsub("\\", "/"):gsub("/tests$", "")
  local fixture_appdata = os.getenv("APPDATA")
  local io_root = fixture_appdata .. "\\Balatro\\agent_io"
  local fixture_time = os.time() + 0.456
  local run_id = tostring(math.floor(fixture_time * 1e9)) .. "-1234"
  local file_run_id = run_id:gsub("[^%w_-]", "_")

  love.timer.getTime = function() return fixture_time end
  os.clock = function() return _G.fixture_clock end
  _G.fixture_clock = 0
  math.random = function() return 1234 end
  os.getenv = function(name)
    if name == "APPDATA" then return _G.fixture_appdata end
    return nil
  end
  _G.fixture_appdata = fixture_appdata

  _G.G = {
    STAGE = 1,
    STAGES = { RUN = 1 },
    STATE = 1,
    STATES = { GAME_OVER = 99 },
    GAME = { won = false },
    FUNCS = {},
    E_MANAGER = {events = {}},
    VERSION = "fixture",
  }
  function G.E_MANAGER:add_event(event)
    self.events[#self.events + 1] = event
    return event
  end
  _G.ease_dollars = function(amount)
    G.GAME.dollars = G.GAME.dollars + amount
  end
  _G.Card = {
    use_consumeable = function(self)
      if self.config.center.key == "c_hermit" then
        G.E_MANAGER:add_event({func = function()
          if not _G.skip_hermit_effect then
            ease_dollars(math.max(0, math.min(G.GAME.dollars, self.ability.extra)))
          end
          return true
        end})
      end
    end,
    calculate_joker = function(self, context)
      if self.config.center.key == "j_mail" and context.discard
          and context.other_card:get_id() == G.GAME.current_round.mail_card.id
          and not context.other_card.debuff then
        ease_dollars(self.ability.extra)
      end
      return "rebate-result"
    end,
  }
  local forwarded_args, forwarded_extra
  _G.Game = { start_run = function(self, args, extra)
    forwarded_args, forwarded_extra = args, extra
    return "started", extra
  end }
  _G.win_game = function() return "won" end

  local ok, bridge = pcall(dofile, root .. "/ground_truth/balatro_mod/main.lua")
  if not ok then return fail(tostring(bridge)) end

  -- Continue without an in-process identity must still allocate a producer ID.
  Game:start_run({savetext = "cold save"})

  bridge.emit("PlayHand")
  _G.fixture_clock = 1
  bridge.emit("DiscardHand")

  local first = io_root .. "\\request_" .. file_run_id .. "_000000000001.json"
  local second = io_root .. "\\request_" .. file_run_id .. "_000000000002.json"
  local first_file, second_file = io.open(first, "rb"), io.open(second, "rb")
  if not first_file or not second_file then
    if first_file then first_file:close() end
    if second_file then second_file:close() end
    return fail("producer did not retain both queued request files")
  end
  local first_text, second_text = first_file:read("*a"), second_file:read("*a")
  first_file:close()
  second_file:close()
  if not first_text:find('"request_id":1', 1, true)
      or not second_text:find('"request_id":2', 1, true)
      or not first_text:find('"ipc_schema_version":"file-queue/1.0.0"', 1, true) then
    return fail("queue payload identity or protocol version is incorrect")
  end

  G.STATE = G.STATES.GAME_OVER
  bridge.tick()
  local end_file = io.open(io_root .. "\\run_end_" .. file_run_id .. ".json", "rb")
  if not end_file then return fail("producer did not publish run-end watermark") end
  local end_text = end_file:read("*a")
  end_file:close()
  if not end_text:find('"last_request_id":2', 1, true)
      or not end_text:find('"outcome":"loss"', 1, true) then
    return fail("run-end outcome or final request watermark is incorrect")
  end
  _G.fixture_clock = 2
  bridge.emit("PlayHand")
  if io.open(io_root .. "\\request_" .. file_run_id .. "_000000000003.json", "rb") then
    return fail("producer emitted another request after finalization")
  end

  print("producer queue fixture: 2 requests retained; loss watermark=2")

  local function read_file(path)
    local file = io.open(path, "rb")
    if not file then return nil end
    local text = file:read("*a")
    file:close()
    return text
  end
  local function path_for(id, request)
    return io_root .. "\\request_" .. id:gsub("[^%w_-]", "_")
      .. "_" .. string.format("%012d", request) .. ".json"
  end
  local function end_for(id)
    return io_root .. "\\run_end_" .. id:gsub("[^%w_-]", "_") .. ".json"
  end
  fixture_time = fixture_time + 1
  local resumed_id = tostring(math.floor(fixture_time * 1e9)) .. "-1234"
  G.STATE = 1
  G.GAME = {won = false, dollars = 39, chips = 12243, round = 11,
    current_round = {hands_left = 2}, round_resets = {ante = 4}}
  Game:start_run({seed = "new run"})
  for i = 1, 109 do
    _G.fixture_clock = 2 + i
    bridge.emit("PlayHand")
  end
  local boundary = read_file(path_for(resumed_id, 109))
  if not boundary then return fail("new run did not reset request numbering") end
  -- A menu visit is nonterminal, and must not allocate a new identity.
  G.STAGE = 0
  bridge.tick()
  if read_file(end_for(resumed_id)) then return fail("menu finalized the run") end
  fixture_time = fixture_time + 13
  local args = {savetext = "midgame save"}
  local result, extra = Game:start_run(args, "forwarded")
  if forwarded_args ~= args or forwarded_extra ~= "forwarded"
      or result ~= "started" or extra ~= "forwarded" then
    return fail("start_run arguments or return values changed")
  end
  G.STAGE = G.STAGES.RUN
  _G.fixture_clock = 125
  bridge.emit("PlayHand")
  local resumed = read_file(path_for(resumed_id, 110))
  if not resumed or read_file(end_for(resumed_id)) then
    return fail("Continue fragmented or finalized the midgame run")
  end
  for _, field in ipairs({'"ante":4', '"round":11', '"round_score":12243',
      '"hands_left":2', '"dollars":39'}) do
    if not boundary:find(field, 1, true) or not resumed:find(field, 1, true) then
      return fail("midgame fixture state mismatch: " .. field)
    end
  end
  -- Repeated Continue also preserves the watermark.
  Game:start_run(args)
  _G.fixture_clock = 126
  bridge.emit("PlayHand")
  if not read_file(path_for(resumed_id, 111)) then return fail("repeat Continue reset identity") end
  if win_game() ~= "won" then return fail("win hook changed return value") end
  local won = read_file(end_for(resumed_id))
  if not won or not won:find('"last_request_id":111', 1, true)
      or not won:find('"outcome":"win"', 1, true) then
    return fail("resumed run win watermark incorrect")
  end
  Game:start_run(args)
  _G.fixture_clock = 127
  bridge.emit("PlayHand")
  if read_file(path_for(resumed_id, 112)) then return fail("Continue resurrected terminal run") end
  fixture_time = fixture_time + 1
  local next_id = tostring(math.floor(fixture_time * 1e9)) .. "-1234"
  Game:start_run({})
  G.jokers = {cards = {
    {config = {center = {key = "j_ceremonial"}}, ability = {mult = 62}, unique_val = 7001},
    {config = {center = {key = "j_joker"}}, ability = {}, unique_val = 7002, sell_cost = 4},
  }}
  _G.fixture_clock = 128
  bridge.emit("SelectBlind")
  if not read_file(path_for(next_id, 1)) then return fail("New Run retained old identity") end
  G.jokers.cards[1].ability.mult = 70
  G.jokers.cards[2].getting_sliced = true
  bridge.tick()
  local resolved_path = io_root .. "\\mechanics_reference_" .. next_id:gsub("[^%w_-]", "_")
    .. "_000000000001_resolved.json"
  local resolved = read_file(resolved_path)
  if not resolved or not resolved:find('"capture_phase":"resolved"', 1, true)
      or not resolved:find('"victim_sell_cost_pre":4', 1, true)
      or not resolved:find('"mult_before":62', 1, true)
      or not resolved:find('"mult_after":70', 1, true)
      or not resolved:find('"mult_delta":8', 1, true)
      or not resolved:find('"dagger_instance_token":"7001"', 1, true)
      or not resolved:find('"victim_instance_token":"7002"', 1, true) then
    return fail("resolved Dagger reference did not preserve price, values, identity and timing")
  end
  G.STATE = G.STATES.GAME_OVER
  bridge.tick()
  local dagger_end = read_file(end_for(next_id))
  if not dagger_end or not dagger_end:find('"resolved_dagger_reference_count":1', 1, true)
      or not dagger_end:find('"pending_dagger_reference_count":0', 1, true) then
    return fail("terminal Dagger reference watermark does not include resolved sidecar")
  end
  print("producer lifecycle fixture: cold Continue; New Run; menu; Continue 109->110->111; win; no resurrection")
  print("producer Dagger fixture: pre and resolved references retain sell value, mult, identity and timing")

  fixture_time = fixture_time + 1
  local mechanics_run_id = tostring(math.floor(fixture_time * 1e9)) .. "-1234"
  G.STATE = 1
  G.GAME = {won = false, dollars = 9, current_round = {mail_card = {id = 8, rank = "8"}}}
  Game:start_run({})
  local function use_hermit(request_id, dollars, instance_id, skip_effect)
    _G.fixture_clock = _G.fixture_clock + 1
    G.GAME.dollars = dollars
    _G.skip_hermit_effect = skip_effect == true
    bridge.emit("UseConsumable")
    local card = {config = {center = {key = "c_hermit"}}, ability = {extra = 20}, unique_val = instance_id}
    Card.use_consumeable(card)
    local delayed = G.E_MANAGER.events[#G.E_MANAGER.events]
    if not delayed or not delayed.func then return nil end
    delayed.func()
    _G.skip_hermit_effect = false
    bridge.tick()
    return read_file(io_root .. "\\mechanics_reference_"
      .. mechanics_run_id:gsub("[^%w_-]", "_") .. "_" .. string.format("%012d", request_id)
      .. "_mechanics.json")
  end
  local hermit_low = use_hermit(1, 9, 8001)
  local hermit_capped = use_hermit(2, 30, 8006)
  local hermit_zero = use_hermit(3, 0, 8007)
  local hermit_unknown = use_hermit(4, 5, 8009, true)
  if not hermit_low or not hermit_low:find('"dollars_before":9', 1, true)
      or not hermit_low:find('"direct_contribution":9', 1, true)
      or not hermit_low:find('"dollars_after":18', 1, true)
      or not hermit_low:find('"source_instance_token":"8001"', 1, true)
      or not hermit_capped or not hermit_capped:find('"direct_contribution":20', 1, true)
      or not hermit_capped:find('"dollars_after":50', 1, true)
      or not hermit_capped:find('"dollars_before":30', 1, true)
      or not hermit_zero or not hermit_zero:find('"direct_contribution":0', 1, true)
      or not hermit_zero:find('"dollars_after":0', 1, true)
      or not hermit_unknown or not hermit_unknown:find('"status":"unknown"', 1, true)
      or not hermit_unknown:find('"direct_contribution":null', 1, true) then
    return fail("Hermit references missed repeated, capped, zero or instance-specific results")
  end

  _G.fixture_clock = _G.fixture_clock + 1
  bridge.emit("DiscardHand")
  local rebate = {config = {center = {key = "j_mail"}}, ability = {extra = 5}, unique_val = 8002}
  local rebate2 = {config = {center = {key = "j_mail"}}, ability = {extra = 5}, unique_val = 8005}
  local function playing_card(token, rank)
    return {unique_val = token, base = {value = rank}, debuff = false,
      get_id = function(self)
        if self.base.value == "8" then return 8 end
        if self.base.value == "9" then return 9 end
        return 7
      end}
  end
  local card8 = playing_card(8003, "8")
  Card.calculate_joker(rebate, {discard = true, other_card = card8})
  Card.calculate_joker(rebate, {discard = true, other_card = card8})
  local card7 = playing_card(8004, "7")
  Card.calculate_joker(rebate, {discard = true, other_card = card7})
  bridge.tick()
  local rebate_reference = read_file(io_root .. "\\mechanics_reference_"
    .. mechanics_run_id:gsub("[^%w_-]", "_") .. "_000000000005_mechanics.json")
  if not rebate_reference or not rebate_reference:find('"trigger":"mail_in_rebate"', 1, true)
      or not rebate_reference:find('"target_rank":"8"', 1, true)
      or not rebate_reference:find('"discarded_rank":"8"', 1, true)
      or not rebate_reference:find('"trigger_multiplicity":2', 1, true)
      or not rebate_reference:find('"direct_contribution":10', 1, true)
      or not rebate_reference:find('"discarded_rank":"7"', 1, true)
      or not rebate_reference:find('"direct_contribution":0', 1, true) then
    return fail("Mail-In Rebate references missed target/rank, multiplicity, zero participation or contribution: "
      .. tostring(rebate_reference))
  end

  G.GAME.current_round.mail_card = {id = 9, rank = "9"}
  _G.fixture_clock = _G.fixture_clock + 1
  bridge.emit("DiscardHand")
  local card9 = playing_card(8008, "9")
  Card.calculate_joker(rebate, {discard = true, other_card = card9})
  Card.calculate_joker(rebate, {discard = true, other_card = card9})
  Card.calculate_joker(rebate2, {discard = true, other_card = card9})
  bridge.tick()
  local changed_rank = read_file(io_root .. "\\mechanics_reference_"
    .. mechanics_run_id:gsub("[^%w_-]", "_") .. "_000000000006_mechanics.json")
  if not changed_rank or not changed_rank:find('"target_rank":"9"', 1, true)
      or not changed_rank:find('"discarded_rank":"9"', 1, true)
      or not changed_rank:find('"trigger_multiplicity":2', 1, true)
      or not changed_rank:find('"direct_contribution":10', 1, true)
      or not changed_rank:find('"rebate_instance_token":"8005"', 1, true)
      or not changed_rank:find('"direct_contribution":5', 1, true) then
    return fail("Rebate rank snapshot or multiple-instance semantics were not retained")
  end
  G.STATE = G.STATES.GAME_OVER
  bridge.tick()
  local mechanics_end = read_file(end_for(mechanics_run_id))
  if not mechanics_end or not mechanics_end:find('"resolved_mechanics_reference_count":6', 1, true)
      or not mechanics_end:find('"pending_mechanics_reference_count":0', 1, true) then
    return fail("terminal mechanics reference watermark omitted resolved Hermit/Rebate scenarios")
  end
  print("producer mechanics fixture: repeated/capped/zero Hermit; Rebate rank change, mixed ranks, retrigger and multiple instances")
  love.event.quit(0)
end
