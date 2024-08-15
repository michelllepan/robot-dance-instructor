import yaml


def get_config():
    with open("config.yml") as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
    return cfg