PDF Toolbox - Kylin / Linux Install Guide
=========================================

RECOMMENDED (no unzip needed for inner package)
-----------------------------------------------
1. Download from GitHub Releases (direct file, NOT Artifacts zip):
   PdfToWord-Kylin-x86_64.run

2. In terminal:
   chmod +x PdfToWord-Kylin-x86_64.run
   ./PdfToWord-Kylin-x86_64.run

   The .run file extracts to a temp folder and starts the app automatically.


IF YOU DOWNLOADED FROM ACTIONS (outer zip)
------------------------------------------
GitHub wraps files in PdfToWord-Kylin.zip. If the archive manager fails:

  sudo apt install unzip
  unzip PdfToWord-Kylin.zip

Or use Python (usually pre-installed on Kylin):

  python3 -m zipfile -e PdfToWord-Kylin.zip .

Then choose ONE of:

  A) Self-extracting (easiest):
     chmod +x PdfToWord-Kylin-x86_64.run
     ./PdfToWord-Kylin-x86_64.run

  B) tar.gz:
     tar -xzf PdfToWord-Kylin-x86_64.tar.gz
     cd PdfToWord
     chmod +x run.sh PdfToWord check-kylin.sh
     ./run.sh


MANUAL RUN (after extracting tar.gz)
------------------------------------
  cd PdfToWord
  chmod +x run.sh PdfToWord check-kylin.sh
  ./check-kylin.sh    # optional environment check
  ./run.sh


TROUBLESHOOTING
---------------
Missing libraries:
  sudo apt install libgl1 libglib2.0-0 libxkbcommon0 libxcb-xinerama0

Cannot unzip at all:
  - Use Releases page for direct .run download
  - Or: sudo apt install p7zip-full && 7z x PdfToWord-Kylin.zip
