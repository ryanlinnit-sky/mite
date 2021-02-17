import json
from multiprocessing import Process
from unittest import mock

import pytest
import ujson
from pytest_httpserver.httpserver import HandlerType
from werkzeug.wrappers import Response

from mite.__main__ import _controller_log_end, _controller_log_start
from mite.__main__ import controller as main_controller
from mite.__main__ import duplicator as main_duplicator
from mite.__main__ import runner as main_runner
from mite.config import ConfigManager
from mite.controller import Controller, WorkTracker
from mite.scenario import ScenarioManager, StopScenario

TESTNAME = "unit_test_name"


def test_controller_hello():
    scenario_manager = ScenarioManager()
    config_manager = ConfigManager()
    controller = Controller(TESTNAME, scenario_manager, config_manager)
    for i in range(5):
        runner_id, test_name, config_list = controller.hello()
        assert test_name == controller._testname
        assert runner_id == i + 1


def test_controller_log_start(httpserver):
    def handler(req):
        assert req.data == json.dumps({"id": "testing"}).encode("utf-8")
        return

    httpserver.expect_request(
        "/start",
        "POST",
        data=ujson.dumps({"testname": "testing"}),
        handler_type=HandlerType.ONESHOT,
    ).respond_with_json({"newid": "testing-id"})

    with httpserver.wait(raise_assertions=True, stop_on_nohandler=True, timeout=5):
        _controller_log_start("testing", httpserver.url_for("/"))


def test_controller_log_end(httpserver):
    httpserver.expect_request(
        "/end",
        "POST",
        data=ujson.dumps({"id": "testing-id"}),
        handler_type=HandlerType.ONESHOT,
    ).respond_with_response(Response(status=204))

    with httpserver.wait(raise_assertions=True, stop_on_nohandler=True, timeout=5):
        _controller_log_end("testing-id", httpserver.url_for("/"))


# TODO: a proper mini-integration test for the logging webhook (to assure it's
# called at both beginning and end).  I haven't yet figured out how to get the
# controller stuff in __main__.py to work properly without hanging, which is
# a prerequisite of this


class DummySender:
    def __init__(self, *args, **kwargs):
        self._received = []

    def send(self, msg):
        self._received.append(msg)


def dummy_vm(s, e):
    if s > 10:
        raise StopScenario
    return 1


async def dummy_journey(ctx):
    pass


def dummy_scenario():
    return [("test_controller:dummy_journey", None, dummy_vm)]


@pytest.mark.slow
@pytest.mark.skip(reason="it causes the whole process to abort! :(")
def test_controller_report():
    # breakpoint()
    ds = DummySender()
    opts = {
        "SCENARIO_SPEC": "test_controller:dummy_scenario",
        "--delay-start-seconds": 0,
        "--min-loop-delay": 0,
        "--max-loop-delay": 0,
        "--spawn-rate": 2000,
        "--message-backend": "ZMQ",
        "--config": "mite.config:default_config_loader",
        "--add-to-config": (),
        "--controller-socket": "tcp://127.0.0.1:14301",
        "--logging-webhook": None,
        "--message-socket": "tcp://127.0.0.1:14302",
        "--runner-max-journeys": None,
        "--debugging": None,
        "OUT_SOCKET": (),
    }
    runner = Process(target=main_runner, args=(opts,))
    runner.start()
    duplicator = Process(target=main_duplicator, args=(opts,))
    duplicator.start()
    with mock.patch("mite.__main__._create_sender", return_value=ds):
        main_controller(opts)
    runner.terminate()
    duplicator.terminate()
    # Even in a broken condition, we get one controller report.  So we check
    # that we have more than that...
    assert sum(x["type"] == "controller_report" for x in ds._received) > 1


class TestWorkTracker:
    example_work = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

    def test_get_total_work_is_additive(self):
        wt = WorkTracker()
        wt.set_actual(1, {101: 3})
        wt.set_actual(2, {101: 3})
        total = wt.get_total_work([1, 2])
        assert total == {101: 6}

    def test_remove_runner_removes_work_from_total(self):
        wt = WorkTracker()
        wt.set_actual(1, {101: 3})
        wt.set_actual(2, {101: 3})
        wt.remove_runner(1)
        total = wt.get_total_work([2])
        assert total == {101: 3}

    def test_add_assumed(self):
        wt = WorkTracker()
        assumed = (
            (1, None, None, None),
            (1, None, None, None),
            (1, None, None, None),
            (1, None, None, None),
            (2, None, None, None),
        )
        wt.add_assumed(1, assumed)
        assert wt._all_work[1] == {1: 4, 2: 1}

    def test_remove_runner(self):
        work_tracker = WorkTracker()
        for i in range(1, 6):
            work_tracker.set_actual(i, {i: 1})
        for i in range(1, 6):
            work_tracker.remove_runner(i)
            assert i not in work_tracker._all_work

    def test_set_actual(self):
        work_tracker = WorkTracker()
        work_tracker.set_actual(1, self.example_work)
        assert work_tracker._all_work[1] == self.example_work

    def test_add_assume(self):
        work_tracker = WorkTracker()
        for i in range(5):
            work_tracker.add_assumed(i, self.example_work)
        assert work_tracker._total_work == {
            1: 1 * 5,
            2: 2 * 5,
            3: 3 * 5,
            4: 4 * 5,
            5: 5 * 5,
        }
