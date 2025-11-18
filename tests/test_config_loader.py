from config.loader import ConfigLoader


def test_config_loader_tor_defaults():
    cl = ConfigLoader()
    # default.yml has tor.enabled set to false by default
    val = cl.get("tor.enabled")
    assert val in (False, None)
