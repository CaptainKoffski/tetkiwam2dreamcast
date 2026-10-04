# Tetris Kiwamemichi -- Naomi->DC conversion. Top-level build
# (modeled on ../senkosp2dreamcast/Makefile).
#
#   make gdi     = build/gdi/tetris.gdi + track01..04 (build_gdi.py; reads the
#                  romset from ../naomi2dreamcast/naomi, override NAOMI_DIR=)
#   make disc    = alias for gdi
#   make verify  = check build/gdi against the 0.4.0 reference SHA1s (README;
#                  they assume iplogo.mr + 0GDTEX.PVR at the repo root)
#   make release = "build/[GDI] Tetris Kiwamemichi.zip": gdi + 4 tracks in a
#                  "Tetris Kiwamemichi/" folder (Sushi Bar / Dolphin Blue
#                  convention). CONTAINS THE COMMERCIAL GAME -- local use only,
#                  never upload/commit (build/ is gitignored for this reason).
#   make deploy CARD=/Volumes/GDEMU/NN = copy the five disc files to a GDEMU
#                  card entry + dot_clean + eject (NOEJECT=1 to stage more)
#   make clean   = rm build/gdi, the release zip, build/extract_dat
#
# Requires: chdman, clang++, python3 (README §Build).

OUT = build/gdi
DISC_FILES = $(OUT)/tetris.gdi $(OUT)/track01.bin $(OUT)/track02.raw \
             $(OUT)/track03.iso $(OUT)/track04.iso
GAMEDIR = Tetris Kiwamemichi
ZIP = build/[GDI] $(GAMEDIR).zip
CARD ?= /Volumes/GDEMU/03

.PHONY: gdi disc verify release deploy clean

gdi:
	python3 build_gdi.py $(OUT)

disc: gdi

verify:
	cd $(OUT) && printf '%s  %s\n' \
	  1d6069f79206f488393963711ad6859a134c6b8f tetris.gdi \
	  5cf394175d4caad3b37b8f4ec213cb7b81d9a71f track01.bin \
	  6030e25dac2e9c0237aaf908b5037ee16503e0c0 track02.raw \
	  05ab2d08d33d637e8f73f971d8387af6321fe274 track03.iso \
	  2718605b6947bad281ea81283212cccb1f29d534 track04.iso | shasum -c

release: gdi
	rm -rf "$(ZIP)" "build/release/$(GAMEDIR)"
	mkdir -p "build/release/$(GAMEDIR)"
	ln -f $(DISC_FILES) "build/release/$(GAMEDIR)/"
	cd build/release && zip -r "../../$(ZIP)" "$(GAMEDIR)"
	@echo "NOTE: the archive embeds the commercial game -- do not upload."

# Sibling's deploy recipe (../senkosp2dreamcast/Makefile, from ../cleopatra):
# copy, dot_clean, then fail loudly if any ._* AppleDouble sidecar survived --
# GDEMU reads the junk `.gdi` first. No default CARD: the sibling ports own
# other slots on the same card.
deploy: gdi
	test -n "$(CARD)" || { echo "usage: make deploy CARD=/Volumes/GDEMU/NN"; exit 1; }
	test -d "$(CARD)"   # card entry mounted?
	cp $(DISC_FILES) "$(CARD)/"
	dot_clean -m "$(CARD)"
	@ls -a "$(CARD)" | grep '^\._' && { echo "AppleDouble junk survived!"; exit 1; } || true
	$(if $(NOEJECT),@echo "deployed to $(CARD) -- NOT ejected",\
	  diskutil eject "$$(df '$(CARD)' | tail -1 | awk '{print $$NF}')")

clean:
	rm -rf $(OUT) build/release "$(ZIP)" build/extract_dat
