# This makefile allows easy installation of the application from
# a Yocto recipe and also deploying the application over ssh
# during development.

# Hostname for the "deploy" target. scp is used to copy the files,
# so you should have set that up in advance.
DEPLOY_HOST ?= kobo-clara-hd

# Username for the "deploy" target.
DEPLOY_USER ?= koboapp

APP_FILES = \
	app/__init__.py \
	app/config.py \
	app/utils.py \
	config/template.yaml \
	hass/__init__.py \
	hass/client.py \
	hass/types.py \
	model/__init__.py \
	model/battery.py \
	model/entitystore.py \
	model/timedate.py \
	model/usb.py \
	model/wifi.py \
	ui/__init__.py \
	ui/data/__init__.py \
	ui/data/fonts/__init__.py \
	ui/data/fonts/MaterialDesignIconsDesktop.ttf \
	ui/data/fonts/MDI_meta.json \
	ui/data/fonts/Roboto-Regular.ttf \
	ui/data/fonts/Roboto-Black.ttf \
	ui/data/fonts/Roboto-Italic.ttf \
	ui/config.py \
	ui/resources.py \
	ui/utils.py \
	ui/widgets.py \
	haslate.py \
	LICENSE

BUILD_DIR = build
DESTDIR ?= $(CURDIR)/install

BUILT_FILES = $(addprefix $(BUILD_DIR)/,$(APP_FILES))

.PHONY: build
build: $(BUILT_FILES)

$(BUILT_FILES): $(BUILD_DIR)/%: %
	install -D "$<" "$@"

.PHONY: install
install: $(BUILT_FILES) | $(DESTDIR)
	cd $(BUILD_DIR) && cp -R --no-preserve=ownership * $(DESTDIR)/

.PHONY: deploy
deploy: $(BUILT_FILES)
	scp -r $(BUILD_DIR)/* $(DEPLOY_USER)@$(DEPLOY_HOST):/home/$(DEPLOY_USER)/haslate/

.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)
