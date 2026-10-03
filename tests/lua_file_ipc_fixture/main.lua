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

  local ok, bridge = pcall(dofile, root .. "/ground_truth/balatro_mod/main.lua")
  if not ok then return fail(tostring(bridge)) end

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
  love.event.quit(0)
end
