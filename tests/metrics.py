import json
import os
import pexpect
import pytest
from contextlib import contextmanager


@contextmanager
def environment_as(config_data):
    """
    Context manager: Set up environment for metrics testing, or fail if there's
    something wrong in the environment which can't be fixed.

    If `config_data` is not None, write it as JSON to the config file and
    remove it again after the wrapped code runs.
    """
    assert os.environ.get('DEVSTACK_METRICS_TESTING'), \
        "You need a DEVSTACK_METRICS_TESTING=debug if running this test " \
        "locally since this environment variable both enables printing of " \
        "metrics and also marks sent metric events as test data."
        
    config_dir = os.path.expanduser('~/.config/devstack')
    config_path = os.path.join(config_dir, 'metrics.json')

    assert not os.path.isfile(config_path), \
        "You already have a config file; failing now to avoid overwriting it."

    if config_data is not None:
        os.makedirs(config_dir, exist_ok=True)
        with open(config_path, 'w') as f:
            f.write(json.dumps(config_data))

    try:
        yield
    finally:
        # Clean up before exiting.
        if config_data is not None:
            with open(config_path, 'r') as f:
                # For debugging...
                print("Metrics config file in effect was: " + f.read())

        try:
            os.remove(config_path)
        except FileNotFoundError:
            pass


def test_feature_flag_missing():
    """
    Test that metrics collection does not happen with feature flag missing.
    """
    with environment_as(None):
        p = pexpect.spawn('make dev.up.redis', timeout=60)
        with pytest.raises(pexpect.EOF):
            p.expect(r'Send metrics info:')


def test_feature_flag_false():
    """
    Test that metrics collection does not happen with feature flag set to False.
    """
    with environment_as({'collection_enabled': False}):
        p = pexpect.spawn('make dev.up.redis', timeout=60)
        with pytest.raises(pexpect.EOF):
            p.expect(r'Send metrics info:')


def test_no_arbitrary_target_instrumented():
    """
    Test that arbitrary make targets are not instrumented.
    """
    with environment_as({'collection_enabled': True}):
        p = pexpect.spawn('make xxxxx', timeout=60)
        with pytest.raises(pexpect.EOF):
            p.expect(r'Send metrics info:')


def test_metrics():
    """
    Test that dev.up.% is instrumented for metrics collection.
    """
    with environment_as({'collection_enabled': True}):
        p = pexpect.spawn('make dev.up.redis', timeout=60)
        p.expect(r'Send metrics info:')
        p.expect(r'dev\.up\.redis')