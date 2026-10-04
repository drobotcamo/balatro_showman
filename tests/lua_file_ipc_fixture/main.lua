local function fail(message)
  io.stderr:write("producer queue fixture failed: " .. message .. "\n")
  love.event.quit(1)
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
    VERSION = "fixture",
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
  _G.fixture_clock = 128
  bridge.emit("PlayHand")
  if not read_file(path_for(next_id, 1)) then return fail("New Run retained old identity") end
  print("producer lifecycle fixture: cold Continue; New Run; menu; Continue 109->110->111; win; no resurrection")
  love.event.quit(0)
end
