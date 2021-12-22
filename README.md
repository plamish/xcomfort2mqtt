# xcomfort2mqtt
AppDaemon xComfort to MQTT broker.

Installation on Home Assistant:
1) Install AppDaemon 4 in Configuration -> Add-ons 
2) Upload apps.yaml & xc2mqtt.py to HA folder /config/appdaemon/apps
3) Edit configuration in /config/appdaemon/apps/apps.yaml

For app log you is necessery to open AppDeamon Web UI from  HA -> Configuration -> Add-ons -> AppDaemon 4

For tracking MQTT messages MQTT Explorer will be good

HA sensors can be created with one of MQTT templates: https://www.home-assistant.io/integrations/#search/mqtt

For xComfort actuators integration go to https://github.com/plamish/xcomfort
