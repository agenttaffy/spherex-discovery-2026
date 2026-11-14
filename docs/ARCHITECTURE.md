# SPHEREx Discovery — System Architecture

```text
+-------------------------------------------------------------------------------+
|                             CLIENT (React 18 + Vite)                          |
|                                                                               |
|  +---------------------+  +-------------------------+  +-------------------+  |
|  |   SearchControls    |  |       CanvasViewer      |  |   MetadataPanel   |  |
|  | - RA / Dec (deg/sex)|  | - Canvas 2D image render|  | - UTC Obs Time    |  |
|  | - FOV selector      |  | - Pan & Zoom (matrix)   |  | - Detector / Band |  |
|  | - Target Presets    |  | - Crosshair coordinate  |  | - Quality flags   |  |
|  | - Collection select |  | - Stretch: asinh/zscale |  | - IRSA Access URL |  |
|  +---------------------+  +-------------------------+  +-------------------+  |
|                                        ^                                      |
|                                        |                                      |
|  +-------------------------------------+-----------------------------------+  |
|  |                 TimelinePlayer & BlinkComparator                        |  |
|  |   [<< Prev]  [ Play / Pause ]  [Next >>]   [Speed: 2 fps]  [Blink: On]  |  |
|  +-------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------+
                                         |
                                         | HTTP REST API
                                         v
+-------------------------------------------------------------------------------+
|                        BACKEND (FastAPI / Python 3.11)                        |
|                                                                               |
|  +--------------------+  +-----------------------+  +-----------------------+ |
|  |  /api/health       |  |  /api/observations    |  |  /api/frames/{id}     | |
|  |  Service health,   |  |  Query NASA IRSA SIA2 |  |  Fetches FITS cutout, | |
|  |  NASA connectivity |  |  Returns obs list     |  |  renders PNG / WebP   | |
|  +--------------------+  +-----------------------+  +-----------------------+ |
|                                        |                                      |
|         +------------------------------+-------------------------------+      |
|         v                              v                               v      |
|  +--------------------+  +---------------------------+  +-------------------+ |
|  |   irsa_client.py   |  |    fits_processing.py     |  | cache_service.py  | |
|  | - SIA2 query builder|  | - Multi-extension parsing |  | - Local FITS disk | |
|  | - TAP obscore      |  | - WCS celestial extract   |  |   caching         | |
|  | - Error handling   |  | - Quality bitmask check   |  | - Manifest cache  | |
|  |                    |  | - asinh/percentile render |  |                   | |
|  +--------------------+  +---------------------------+  +-------------------+ |
+-------------------------------------------------------------------------------+
                                         |
                                         | HTTPS (VOTable / CSV / FITS)
                                         v
+-------------------------------------------------------------------------------+
|                           NASA / IPAC IRSA SERVICES                           |
|  - IRSA SIA2 Endpoint: /SIA?COLLECTION=spherex_dr1...                         |
|  - IRSA IBE Cutout Service: /ibe/data/spherex/...fits?center=...&size=...     |
+-------------------------------------------------------------------------------+
```
