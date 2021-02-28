# <a name="ESPHome">ESPHome</a>

For various wireless devices around the house, I use [ESPHome](https://esphome.io/index.html) (see [Home Assistant integration](https://www.home-assistant.io/integrations/esphome/)).

The current devices I use are as follows:
| Node name | Type | Components | Notes |
| ------------- | :---: | ------------- | ---------- |
| [ambilightleft](#atmoorbs) | Light | [WS2812 LED ring](https://www.banggood.com/WS2812B-35-Bits-5050-RGB-DIY-LED-Module-Strip-Ring-Light-with-Integrated-Drivers-Board-DC5V-p-1491080.html) |  |
| [ambilightright](#atmoorbs) | Light | [WS2812 LED ring](https://www.banggood.com/WS2812B-35-Bits-5050-RGB-DIY-LED-Module-Strip-Ring-Light-with-Integrated-Drivers-Board-DC5V-p-1491080.html) |  |
| [falconlights](#falcon) | Light | [APA102 LED strip](https://www.aliexpress.com/item/32969463242.html) |  |
| [stardestroyerlights](#ssdlights) | Light | 2x [WS2801 LED strip](https://www.aliexpress.com/item/32311011586.html) |  |
| [bed_scale](#Bedscale) | Sensor | hx711 + 4x load cell | Used to measure bed weight to determine bed presence |
| [CO2_sensor](#CO2sensor) | Sensor | MH-Z19b | Used to measure the CO2 concentration in the bedroom |

# <a name="Ambilight">Ambilight</a>
I use [Hyperion](https://github.com/hyperion-project/hyperion.ng) to provide Ambilight for my TV. Hyperion forwards the data to the three LED strips connected to a Lego Millennium Falcon and a Lego Super Star Destroyer. The configs can be found under [esphome](./esphome).
- [ ] Component list with links for AtmoOrbs
- [ ] Component list with links for Falconlights
- [ ] Component list with links for SSDlights
- [ ] Document Hyperion configuration
- [ ] Document used protocol
- [ ] Link to scripts in ./areas/mediacenter.yaml

## <a name="atmoorbs">AtmoOrbs</a>:

<img src="www/readme_images/AtmoOrb_withoutbulb.png" width=500><img src="www/readme_images/AtmoOrb_withbulb.png" width=500>

The AtmoOrbs are made up by a NodeMCU board connected to a [LED ring with 35 integrated WS2812 LEDs](https://www.banggood.com/WS2812B-35-Bits-5050-RGB-DIY-LED-Module-Strip-Ring-Light-with-Integrated-Drivers-Board-DC5V-p-1491080.html) built inside an [Ikea Fado lamp](https://www.ikea.com/nl/en/p/fado-table-lamp-white-80096372/). The lamp requires a bit of modification to fit the LED ring, and I have designed a [holder](https://www.thingiverse.com/thing:4777153) to fix the ring and NodeMCU to the lamp base. The color data is sent from Hyperion to the NodeMCU via the UDP E1.31 protocol, and there is no noticable delay.

## <a name="falcon">Falconlights</a>:

<img src="www/readme_images/Falcon.png" width=500>

## <a name="ssdlights">Star Destroyer Lights</a>:

<img src="www/readme_images/superstardestroyer.png" width=500>
<!-- ![alt text](www/readme_images/AtmoOrb_withoutbulb.png)
![alt text](www/readme_images/AtmoOrb_withbulb.png)
![alt text](www/readme_images/Falcon.png)
![alt text](www/readme_images/superstardestroyer.png) -->

# <a name="Sensors">Sensors</a>

## <a name="CO2sensor">CO2 Sensor</a>
<img src="www/readme_images/CO2_sensor.png" width=500>

<img src="www/readme_images/CO2_sensor_example_data.png" width=700>

## <a name="Bedscale">Bed scale</a>
