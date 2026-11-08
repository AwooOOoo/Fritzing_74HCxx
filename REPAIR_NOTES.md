# Library packaging and four-part DIP-14 corrections

The downloadable artifact remains one file: `74HCxx Series.fzbz`. Original module IDs, connector IDs and connector geometry are preserved for compatibility. The archive contains 32 distinct bin entries, with all referenced definitions and SVG files included.

## Packaging repairs

- Recover the 12 omitted definitions from this repository's existing `images/all_chips.fzz`: 74HC86, 138, 139, 151, 161, 181, 245, 273, 283, 299, 595 and 4078.
- Rebind missing view references to the corresponding existing library SVGs (including 74HC20 and the recovered definitions whose asset names differ).
- Remove two duplicate 74HC4851 bin instances, retain one instance, replace author-machine absolute paths with relative part filenames, and remove the reference to an unbundled Custom1.png bin icon.
- Match the icon SVG group ID to the declared icon layer for all parts. Other views retain their original geometry.
- Correct README `70HC` prefixes to `74HC` and document the importable archive.

These are packaging checks for the full library; they do not establish the electrical pin correctness of all 32 parts.

## Datasheet-based corrections: 74HC00, 74HC04, 74HC20, 74HC86

| Part | Finding and correction |
|---|---|
| 74HC00 | Pin mapping agrees with TI; correct the HCT variant metadata to HC. |
| 74HC04 | Physical pin 2 / connector1 was named 1B although the schematic already displayed 1Y. Rename it to 1Y; fix the truncated output description at pin 6 and HCT metadata. |
| 74HC20 | Physical pin 6 / connector5 and its visible schematic label were pin61Y. Correct both to 1Y. Its four resource references pointed to absent filenames; bind them to the actual bundled SVGs. Pins 3 and 11 remain NC. |
| 74HC86 | Restore the omitted definition and correct its references and HCT metadata. Its 14 schematic pin labels had font-size 540.123, obscuring the symbol; use 41.6667. |

For these four parts, normalize VCC/NC names and show the chip number instead of the generic IC schematic label. No gate pin is moved or renumbered. They use package-style schematic symbols, not individual gate symbols or simulation models.

The README's `70HC20` was a spelling error, but the actual 74HC20 had independent definition/resource errors.

Reference pin order, physical pins 1 through 14 (connector0 through connector13):

| Part | Names |
|---|---|
| 74HC00 | 1A, 1B, 1Y, 2A, 2B, 2Y, GND, 3Y, 3A, 3B, 4Y, 4A, 4B, VCC |
| 74HC04 | 1A, 1Y, 2A, 2Y, 3A, 3Y, GND, 4Y, 4A, 5Y, 5A, 6Y, 6A, VCC |
| 74HC20 | 1A, 1B, NC, 1C, 1D, 1Y, GND, 2Y, 2A, 2B, NC, 2C, 2D, VCC |
| 74HC86 | 1A, 1B, 1Y, 2A, 2B, 2Y, GND, 3Y, 3A, 3B, 4Y, 4A, 4B, VCC |

Sources: TI SN74HC00 SCLS181B (May 1997), SN74HC04 SCLS078B (May 1997), SN74HC20 SCLS086D (February 2000), SN74HC86 SCLS100E (August 2003), each page 1, N-package top-view pinout. Manufacturer links: [00](https://www.ti.com/product/SN74HC00), [04](https://www.ti.com/product/SN74HC04), [20](https://www.ti.com/product/SN74HC20), [86](https://www.ti.com/product/SN74HC86). Later datasheet revisions may have different pagination.

## Validation and limits

Run with Python 3, no third-party dependencies:

```sh
python tools/repair_library.py --check
```

This checks ZIP integrity, unique bin instances, inclusion of all referenced definitions, module IDs, SVG references, unique SVG IDs, layers and connector/terminal IDs. For the four parts it also checks all 56 pin names/IDs, 0.1-inch pitch and 0.3-inch breadboard row spacing, schematic terminal positions and visible pin labels/font size. Independent SVG previews of these four parts were visually checked; the integrated archive uses exactly those same SVG bytes.

`python tools/repair_library.py` rebuilds the archive from its current contents and the author's sketch, then validates before replacing it. Rebuilding the repaired archive is byte-idempotent.

Not tested: actual Fritzing GUI import, breadboard snapping, wire creation, view synchronization, or save/reopen. The independent SVG preview renderer is not Fritzing's Qt renderer. PCB resources are checked for structural completeness only, not drill/pad dimensions or manufacturability. The other 28 parts have not been checked against manufacturer pinouts. This change is not a full electrical audit or a claim that every library defect is resolved.
