# HACS Sengled for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

**This is incomplete beta code.**

This is a [HACS](https://hacs.xyz/) integration to connect Sengled Wifi lights to [Home Assistant](https://www.home-assistant.io/). It uses the modernized Platform/Entity and MQTT programming interfaces, but is based on [jfarmer08](https://github.com/jfarmer08)'s [excellent initial work](https://github.com/jfarmer08/ha-sengledapi).

Tested with:

- W21-N13
- W21-N11

## Installation

Install using [HACS](https://hacs.xyz/) (recommended) or copy the contents of this repository into your Home Assistant installation at `config/custom_components/sengledng/`.

## Configuration


Add a `sengledng` section to your `configuration.yaml` and set up your credentials.

```yaml
sengledng:
  username: alice@example.com
  password: !secret sengledng_password
```

## Bugs

Open an [issue](https://github.com/kylev/ha-sengledng/issues) or [pull request](https://github.com/kylev/ha-sengledng/pulls)!
