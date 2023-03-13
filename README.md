## HACS Sengled for Home Assistant

**This is incomplete alpha code.**

This is a HACS integration to connect Sengled Wifi lights to Home Assistant. It uses the modernized Platform/Entity and MQTT programming interfaces, but is based on @jfarmer08's [excellent initial work](https://github.com/jfarmer08/ha-sengledapi).

Tested with:

- W21-N13
- W21-N11

## Configuration

Add your user name (email) and password in the `configuration.yaml`.

```yaml
sengledng:
  username: alice@example.com
  password: !secret sengledng_password
```

## Bugs

Open an [issue](https://github.com/kylev/ha-sengledng/issues) or [pull request](https://github.com/kylev/ha-sengledng/pulls)!
