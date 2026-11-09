# RTL-SDR Antenna Guidelines

This is a practical starting guide for comparing receive antennas with the RTL-SDR. Antenna lengths below assume a **center-fed half-wave dipole**: “per side” means the length of one arm from the feed point to its tip. A dipole has two equal arms.

## Quick length estimate

For a starting physical length, use:

```text
one dipole arm (metres) ≈ 71.3 / frequency (MHz)
```

This is half of the ARRL's common total half-wave dipole estimate, `468 / frequency (MHz)` feet. It is an initial cut length, not a guarantee of best match; conductor thickness, feed arrangement, nearby objects, and installation affect the final result. Leave a little extra length so you can trim it after testing. [ARRL dipole guide](https://www.arrl.org/files/file/Technology/tis/info/pdf/9106023.pdf)

## Bands and antenna choices

| Use | Example frequency | Dipole arm starting length | Antenna type to try |
| --- | ---: | ---: | --- |
| ADS-B | 1090 MHz | 6.5 cm | Vertical quarter-wave ground plane, vertical half-wave dipole, or a purpose-built 1090 MHz antenna. Keep the coax short and low-loss. |
| VHF aviation voice | 118–137 MHz; use about 127.5 MHz for a first cut | 56 cm | Vertical quarter-wave whip with a ground plane, or a vertical dipole. Select an assigned station frequency from the app's list. |
| FM broadcast | 88–108 MHz; about 98 MHz for a first cut | 73 cm | Dipole or folded dipole; orient it to match the local station polarization. A wideband scanner antenna can cover FM and VHF/UHF with compromises. |
| VHF weather satellites | Around 137 MHz | 52 cm | A basic dipole can receive signals; a crossed-dipole turnstile or QFH is a better experiment for satellites moving across the sky. NOAA's receiving-station guide discusses 137–138 MHz antennas and these designs. |
| L-band satellite signals | Depends on service; around 1.5 GHz as an example | About 4.8 cm at 1.5 GHz | Use an antenna designed for the specific satellite service. GNSS commonly uses a patch antenna and ground plane; a short dipole is not a universal satellite antenna. |
| Other VHF/UHF communications | Use the exact receive frequency | Calculate from the formula | A tuned vertical or ground-plane antenna is a reasonable start. “Military band” is not one frequency range; allocations and permitted reception vary by location and service. |
| AM broadcast (medium wave) | Around 1 MHz | About 71 m | A tuned ferrite-rod antenna or loop is practical. A resonant dipole at these frequencies would be extremely large. |

For ADS-B, a quarter-wave ground-plane antenna is a common compact design, and vertical polarization matters. [RTL-SDR ADS-B antenna notes](https://www.rtl-sdr.com/adsb-aircraft-radar-with-rtl-sdr/)

For weather-satellite reception, the NOAA guide covers turnstile and quadrifilar-helix antennas for the 137–138 MHz range. [NOAA satellite receiving-station guide](https://repository.library.noaa.gov/view/noaa/26767/noaa_26767_DS1.pdf)

## Use the new antenna kit

1. Check whether the kit's stated length is for **each element** or for the whole dipole. Measure each arm from its electrical feed point; do not assume that two supplied rods add up to the specified length.
2. Start with one band at a time. Set both dipole arms to the same length and keep their orientation consistent during comparisons.
3. Mount the antenna clear of large metal objects and keep its feed line away from noisy USB hubs, computers, and power supplies where practical.
4. For ADS-B, compare readsb message and position counts over the same period. For airband, use a known active local broadcast such as ATIS when available; silence on a channel can simply mean no transmission at that moment.
5. Change one thing at a time: antenna, height, orientation, feed line, or gain. Record the setup and compare results over similar time windows.
6. Avoid connecting multiple antennas together with a simple Y-splitter. Use a proper RF switch, or a separate receiver for each antenna when you need simultaneous reception.

## One tuner and multiple antennas

There is no single practical dipole length that is resonant for 1090 MHz ADS-B, VHF airband, FM broadcast, satellites, and AM broadcast. For repeatable comparisons, use separate band-tuned antennas and switch them at the receiver. A broadband scanner/discone antenna can cover parts of VHF/UHF, but it will not perform like a tuned antenna on every band and is not a practical AM-broadcast dipole.

The Compose `radio_control` service owns the RTL-SDR exclusively. It runs either readsb for ADS-B or the airband audio pipeline, not both at once. SDR++ provides a native spectrum and waterfall display, so it is the better tool for visual band exploration. The current Station Monitor stays on the curated Hyderabad station presets; adding a waterfall would require a new IQ capture and FFT path and would compete for the same tuner. To use SDR++ with this receiver, first arrange for the controller to release the tuner and make sure SDR++ can access it; do not try to open one USB tuner from both applications at once. [SDR++ user guide](https://www.sdrpp.org/manual.pdf)

All lengths are starting estimates for receive-only experiments. Follow local rules for frequencies and signals you monitor, and do not transmit unless properly licensed and authorized.
