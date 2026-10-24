# Tetris Kiwamemichi -- Naomi->DC conversion. Top-level build
# (modeled on ../senkosp2dreamcast/Makefile).
#
#   make gdi     = build/gdi/tetris.gdi + track01..04 (build_gdi.py; reads the
#                  romset from ../naomi2dreamcast/naomi, override NAOMI_DIR=)
#   make disc    = alias for gdi
#   make cdi     = build/cdi/tetris.cdi + README.txt -- burnable audio/data
#                  MIL-CD for CD-R testers (make_cdi.py: re-masters the built
#                  GDI's files with mkdcdisc + the CD LBA/disc-type patches,
#                  docs/kb/cdi.md; MKDCDISC= to override the mkdcdisc path)
#   make verify  = check build/gdi against the 0.4.0 reference SHA1s (README;
#                  they assume iplogo.mr + 0GDTEX.PVR at the repo root)
#   make release = gdi + cdi + two zips, as in senkosp2dreamcast:
#                  "build/[GDI] Tetris Kiwamemichi.zip" (gdi + 4 tracks in a
#                  "Tetris Kiwamemichi/" folder -- Sushi Bar / Dolphin Blue
#                  convention) and "build/[CDI] Tetris Kiwamemichi.zip"
#                  (tetris.cdi in the same folder + burn README at the root).
#                  BOTH CONTAIN THE COMMERCIAL GAME -- local use only, never
#                  upload/commit (build/ is gitignored for this reason).
#   make deploy  = gdi + cdi onto the inserted GDEMU card (gdemu_deploy.py):
#                  updates the "Tetris Kiwamemichi [GDI]"/"[CDI]" folders or
#                  creates them, rewrites the GDMenu list, dot_clean, eject.
#                  CARD=/Volumes/X if several cards are mounted, NOEJECT=1 to
#                  stage more. `python3 test_gdemu_deploy.py` self-checks it.
#   make clean   = rm build/gdi, build/cdi, the release zips, build/extract_dat
#
# Requires: chdman, clang++, python3; cdi/release also mkdcdisc (README §Build).

OUT = build/gdi
DISC_FILES = $(OUT)/tetris.gdi $(OUT)/track01.bin $(OUT)/track02.raw \
             $(OUT)/track03.iso $(OUT)/track04.iso
GAMEDIR = Tetris Kiwamemichi
ZIP = build/[GDI] $(GAMEDIR).zip
CDI_ZIP = build/[CDI] $(GAMEDIR).zip

.PHONY: gdi disc cdi verify release deploy clean

gdi:
	python3 build_gdi.py $(OUT)

disc: gdi

cdi: gdi
	python3 make_cdi.py $(OUT) build/cdi

verify:
	cd $(OUT) && printf '%s  %s\n' \
	  1d6069f79206f488393963711ad6859a134c6b8f tetris.gdi \
	  5cf394175d4caad3b37b8f4ec213cb7b81d9a71f track01.bin \
	  6030e25dac2e9c0237aaf908b5037ee16503e0c0 track02.raw \
	  05ab2d08d33d637e8f73f971d8387af6321fe274 track03.iso \
	  2cd9232b9c6c50a9a31ce9cf4a36c622e90f1376 track04.iso | shasum -c

release: gdi cdi
	rm -rf "$(ZIP)" "build/release/$(GAMEDIR)"
	mkdir -p "build/release/$(GAMEDIR)"
	ln -f $(DISC_FILES) "build/release/$(GAMEDIR)/"
	cd build/release && zip -r "../../$(ZIP)" "$(GAMEDIR)"
	rm -rf "$(CDI_ZIP)" build/cdi-zip
	mkdir -p "build/cdi-zip/$(GAMEDIR)"
	ln -f build/cdi/tetris.cdi "build/cdi-zip/$(GAMEDIR)/"
	cp build/cdi/README.txt build/cdi-zip/
	cd build/cdi-zip && zip -r "../../$(CDI_ZIP)" .
	@echo "NOTE: both archives embed the commercial game -- do not upload."

deploy: gdi cdi
	CARD="$(CARD)" NOEJECT="$(NOEJECT)" python3 gdemu_deploy.py "$(GAMEDIR)" $(OUT)/tetris.gdi build/cdi/tetris.cdi

clean:
	rm -rf $(OUT) build/cdi build/release build/cdi-zip "$(ZIP)" "$(CDI_ZIP)" build/extract_dat
