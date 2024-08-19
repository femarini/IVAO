# IVAO AURORA SECTORFILE TOOL
DATA EXTRACTOR FROM GEOAISWEB TO .SCT FORMAT (USE ONLY FOR BRAZILIAN AIRSPACE)
#Developed by Fernando Marini - IVAO ID 249151

(Python scripts below are automated and get data directly from the GEOAISWEB website)
TO EXTRACT FIR execute .PY and open the output file (txt).
TO EXTRACT CTA execute .PY and open the output file (txt).
TO EXTRACT TMA execute .PY and open the output file (txt).
TO EXTRACT CTR execute .PY and open the output file (txt).
TO EXTRACT ATZ execute .PY and open the output file (txt).
TO EXTRACT AWY execute .PY and open the output file (txt).
TO EXTRACT APT execute .PY and open the output file (txt). (Airports Only)
TO EXTRACT HEL execute .PY and open the output file (txt). (All Helipads + Airports)
Atention: These output files above may be located at your "C:\Users\yourusername\"

--------------------------------------------------------------------------------
--------------------------------------------------------------------------------

(Python scripts below are not automated and need some files from GEOAISWEB to work)
Download the files here: https://geoaisweb.decea.mil.br/geoserver/web/wicket/bookmarkable/org.geoserver.web.demo.MapPreviewPage?

Required Files:
-> ICA:waypoint_aisweb.xls
-> ICA:vor.xls
-> ICA:ndb.xls

Group these files above with scripts and execute.

TO EXTRACT NDBs use: NDB_EXTRACTOR.py
TO EXTRACT VORs use: VOR_EXTRACTOR.py
TO EXTRACT Fixes use: FIX_EXTRACTOR.py

Atention: These output files above may be located at your "C:\Users\yourusername\"
If you need help contact me on discord @femarini
