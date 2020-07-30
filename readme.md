# Traces

Traces is a Python app for Assetto Corsa. It plots the driver's pedal and steering input telemetry on a graph in real time. Additionally, it includes pedal input bars, a force-feedback meter, steering wheel indicator, speedometer and gear indicator.

![App Preview](/assets/app_preview.png)

## Installation

Install the app by pasting the contents of the .zip file in the main root folder of the Assetto Corsa installation. After this, the app must be activated in the main menu within Assetto Corsa.

## Configuration

The app is user configurable and is integrated with Content Manager. After first launch, options like app size can be tweaked using the config.ini file in the app folder.

## Notes

* Due to the absence of full OpenGL implementation by Kunos for Python apps, the drawing of the telemetry lines is quite resource intensive. This scales directly with the number of input traces (drawing two traces is heavier than one), the sample rate and the time length of the graph.
* Currently when the app is not visible, it still carries out some calculations in the background. This costs some performance and may get fixed in the future.

## Credits

* Rombik, for the Assetto Corsa shared memory library.