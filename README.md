# HACS Sengled for Home Assistant

This is a [HACS](https://hacs.xyz/) integration to connect Sengled Wifi lights to [Home Assistant](https://www.home-assistant.io/). It uses the modernized Platform/Entity and MQTT programming interfaces, but is based on [jfarmer08](https://github.com/jfarmer08)'s [excellent initial work](https://github.com/jfarmer08/ha-sengledapi).

Tested with:

- W21-N13
- W21-N11

## Configuration

Add a `sengledng` section to your `configuration.yaml` and set up your credentials.

```yaml
sengledng:
  username: alice@example.com
  password: !secret sengledng_password
```

## Bugs

Open an [issue](https://github.com/kylev/ha-sengledng/issues) or [pull request](https://github.com/kylev/ha-sengledng/pulls)!
