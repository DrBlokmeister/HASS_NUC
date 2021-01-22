# HASS_NUC

Configuration for [Home Assistant](https://www.home-assistant.io/) running on an [Intel NUC](https://ark.intel.com/content/www/us/en/ark/products/126148/intel-nuc-kit-nuc8i5beh.html) for a three room apartment, offering convenience automations over lights and climate while providing multiple intuitive user controls.

## <a name="hubs">Hubs</a>

| [Go to Menu](#menu) |

| Device  | Quantity | Connection | HA Component | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [Hue Hub v2](https://amzn.to/2IpNA3G)| 1 | Ethernet | [Philips Hue](https://www.home-assistant.io/components/hue/) | Controls all Philips Hue smart lights |
| [Conbee II](https://phoscon.de/en/conbee2)| 1 | USB 2.0 | [deCONZ](https://www.home-assistant.io/integrations/deconz/) | Controls zigbee motion sensors and various other sensors |
| [Xiaomi Aqara Gateway v2](https://xiaomi-mi.com/sockets-and-sensors/xiaomi-mi-gateway-2/)| 1 | Wi-Fi | [Xiaomi Aqara](https://www.home-assistant.io/integrations/xiaomi_aqara/) | Controls a few Xiaomi Aqara sensors not yet transferred to the Conbee II|

## License
[MIT](https://choosealicense.com/licenses/mit/)
## References
[Geekofweek's README.md](https://github.com/geekofweek/homeassistant/blob/master/README.md) was used as a source of inspiration for this document
