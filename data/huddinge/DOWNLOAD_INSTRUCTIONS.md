# Nedladdning av Huddinge WFS-data

Denna mapp innehåller GeoJSON-filer nedladdade från Huddinge kommuns öppna data WFS-tjänst.

## Källa

**WFS:** https://gd-huddinge.sokigohosting.com/public-maps/Oppnadata/MBF

**Token:** `9a11171d115c4a3c841c84f1dba068ef`

## Nedladdningsdatum

2026-07-20

## Lager (Feature Types)

| Fil | Typnamn | Titel |
|-----|---------|-------|
| `jordkallare.geojson` | `qgs:jordkallare` | Jordkällare |
| `gruvhal.geojson` | `qgs:gruvhal` | Gruvhål |
| `mountainbikeleder.geojson` | `qgs:mountainbikeleder` | Mountainbikeleder |
| `dp_plan.geojson` | `qgs:dp_plan` | Detaljplaner |
| `bestammelser_y.geojson` | `qgs:bestammelser_y` | Bestämmelser ytor |
| `bdt.geojson` | `qgs:bdt` | Tillstånd för BDT |
| `vandringsleder.geojson` | `qgs:vandringsleder` | Vandringsleder |
| `friluftsliv.geojson` | `qgs:friluftsliv` | Friluftsliv |
| `kallor.geojson` | `qgs:kallor` | Källor |
| `bestammelser_p.geojson` | `qgs:bestammelser_p` | Bestämmelser punkter |
| `belysningsstolpar.geojson` | `qgs:belysningsstolpar_i_huddinge_kommuns_drift` | Belysningsstolpar i Huddinge kommuns drift |
| `renhallning_punkter.geojson` | `qgs:renhallning_punkter` | Renhållning punkter |
| `vintersandlador.geojson` | `qgs:vintersandlador` | Vintersandlådor |

## Koordinatsystem

WGS84 (EPSG:4326)

## Hur nedladdningen gjordes

### 1. Hämta capabilities för att se tillgängliga lager

```bash
curl -o GetCapabilities.xml "https://gd-huddinge.sokigohosting.com/public-maps/Oppnadata/MBF?SERVICE=WFS&REQUEST=GetCapabilities&token=9a11171d115c4a3c841c84f1dba068ef"
```

### 2. Ladda ner ett enskilt lager

```bash
wget -O <filnamn>.geojson \
  "https://gd-huddinge.sokigohosting.com/public-maps/Oppnadata/MBF?SERVICE=WFS&REQUEST=GetFeature&TYPENAME=qgs:<lager>&OUTPUTFORMAT=application/json&SRSNAME=EPSG:4326&token=9a11171d115c4a3c841c84f1dba068ef"
```

### 3. Exempel: Ladda ner alla lager (parallellt)

```bash
BASE_URL="https://gd-huddinge.sokigohosting.com/public-maps/Oppnadata/MBF?SERVICE=WFS&REQUEST=GetFeature&OUTPUTFORMAT=application/json&SRSNAME=EPSG:4326&token=9a11171d115c4a3c841c84f1dba068ef"

wget -q "${BASE_URL}&TYPENAME=qgs:jordkallare" -O jordkallare.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:gruvhal" -O gruvhal.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:mountainbikeleder" -O mountainbikeleder.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:dp_plan" -O dp_plan.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:bestammelser_y" -O bestammelser_y.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:bdt" -O bdt.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:vandringsleder" -O vandringsleder.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:friluftsliv" -O friluftsliv.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:kallor" -O kallor.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:bestammelser_p" -O bestammelser_p.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:belysningsstolpar_i_huddinge_kommuns_drift" -O belysningsstolpar.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:renhallning_punkter" -O renhallning_punkter.geojson &
wget -q "${BASE_URL}&TYPENAME=qgs:vintersandlador" -O vintersandlador.geojson &
wait
```

## Kom igång med QGIS

Öppna valfri fil i QGIS för att visualisera datan:

```bash
qgis jordkallare.geojson
```

## Obs

- Största filen är `belysningsstolpar.geojson` (4.8 MB) med drygt 21 000 belysningsstolpar
- Vissa lager kan vara tomma (0 features) - kontrollera alltid innan användning
