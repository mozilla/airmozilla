#########################################################################
# common include file for application Makefiles
#
# Makefile Common Usage:
# > make
# > make install
# > make remove
#
# Makefile Less Common Usage:
# > make art-opt
# > make pkg
# > make install_native
# > make remove_native
# > make tr
#
# By default, ZIP_EXCLUDE will exclude -x \*.pkg -x storeassets\* -x keys\* -x .\*
# If you define ZIP_EXCLUDE in your Makefile, it will override the default setting.
#
# To exclude different files from being added to the zipfile during packaging
# include a line like this:ZIP_EXCLUDE= -x keys\*
# that will exclude any file who's name begins with 'keys'
# to exclude using more than one pattern use additional '-x <pattern>' arguments
# ZIP_EXCLUDE= -x \*.pkg -x storeassets\*
#
# Important Notes:
# To use the "install" and "remove" targets to install your
# application directly from the shell, you must do the following:
#
# 1) Make sure that you have the curl command line executable in your path
# 2) Set the variable ROKU_DEV_TARGET in your environment to the IP
#    address of your Roku box. (e.g. export ROKU_DEV_TARGET=192.168.1.1.
#    Set in your this variable in your shell startup (e.g. .bashrc)
##########################################################################
DISTREL = ../dist
COMMONREL = ../common
SOURCEREL = ..

ZIPREL = $(DISTREL)/apps
PKGREL = $(DISTREL)/packages

APPSOURCEDIR = source
IMPORTFILES = $(foreach f,$(IMPORTS),$(COMMONREL)/$f.brs)
IMPORTCLEANUP = $(foreach f,$(IMPORTS),$(APPSOURCEDIR)/$f.brs)

NATIVEDEVREL  = $(DISTREL)/rootfs/Linux86_dev.OBJ/root/nvram/incoming
NATIVEDEVPKG  = $(NATIVEDEVREL)/dev.zip
NATIVETICKLER = $(DISTREL)/application/Linux86_dev.OBJ/root/bin/plethora  tickle-plugin-installer

ifdef DEVPASSWORD
    USERPASS = rokudev:$(DEVPASSWORD)
else
    USERPASS = rokudev
endif

ifndef ZIP_EXCLUDE
  ZIP_EXCLUDE= -x \*.pkg -x storeassets\* -x keys\* -x \*/.\*
endif

HTTPSTATUS = $(shell curl --silent --write-out "\n%{http_code}\n" $(ROKU_DEV_TARGET))

.PHONY: all $(APPNAME)

$(APPNAME): manifest
	@echo "*** Creating $(APPNAME).zip ***"

	@echo "  >> removing old application zip $(ZIPREL)/$(APPNAME).zip"
	@if [ -e "$(ZIPREL)/$(APPNAME).zip" ]; \
	then \
		rm  $(ZIPREL)/$(APPNAME).zip; \
	fi

	@echo "  >> creating destination directory $(ZIPREL)"
	@if [ ! -d $(ZIPREL) ]; \
	then \
		mkdir -p $(ZIPREL); \
	fi

	@echo "  >> setting directory permissions for $(ZIPREL)"
	@if [ ! -w $(ZIPREL) ]; \
	then \
		chmod 755 $(ZIPREL); \
	fi

	@echo "  >> copying imports"
	@if [ "$(IMPORTFILES)" ]; \
	then \
		mkdir $(APPSOURCEDIR)/common; \
		cp -f --preserve=ownership,timestamps --no-preserve=mode -v $(IMPORTFILES) $(APPSOURCEDIR)/common/; \
	fi \

# zip .png files without compression
# do not zip up Makefiles, or any files ending with '~'
	@echo "  >> creating application zip $(ZIPREL)/$(APPNAME).zip"
	@if [ -d $(SOURCEREL)/$(APPNAME) ]; \
	then \
		(zip -0 -r "$(ZIPREL)/$(APPNAME).zip" . -i \*.png $(ZIP_EXCLUDE)); \
		(zip -9 -r "$(ZIPREL)/$(APPNAME).zip" . -x \*~ -x \*.png -x Makefile $(ZIP_EXCLUDE)); \
	else \
		echo "Source for $(APPNAME) not found at $(SOURCEREL)/$(APPNAME)"; \
	fi

	@if [ "$(IMPORTCLEANUP)" ]; \
	then \
		echo "  >> deleting imports";\
		rm -r -f $(APPSOURCEDIR)/common; \
	fi \

	@echo "*** packaging $(APPNAME) complete ***"

#if DISTDIR is not empty then copy the zip package to the DISTDIR.
	@if [ $(DISTDIR) ];\
	then \
		rm -f $(DISTDIR)/$(DISTZIP).zip; \
		mkdir -p $(DISTDIR); \
		cp -f --preserve=ownership,timestamps --no-preserve=mode $(ZIPREL)/$(APPNAME).zip $(DISTDIR)/$(DISTZIP).zip; \
	fi \

install: $(APPNAME)
	@echo "Installing $(APPNAME) to host $(ROKU_DEV_TARGET)"
	@if [ "$(HTTPSTATUS)" == " 401" ]; \
	then \
		curl --user $(USERPASS) --digest -s -S -F "mysubmit=Install" -F "archive=@$(ZIPREL)/$(APPNAME).zip" -F "passwd=" http://$(ROKU_DEV_TARGET)/plugin_install | grep "<font color" | sed "s/<font color=\"red\">//" | sed "s[</font>[[" ; \
	else \
		curl -s -S -F "mysubmit=Install" -F "archive=@$(ZIPREL)/$(APPNAME).zip" -F "passwd=" http://$(ROKU_DEV_TARGET)/plugin_install | grep "<font color" | sed "s/<font color=\"red\">//" | sed "s[</font>[[" ; \
	fi


pkg: install
	@echo "*** Creating Package ***"

	@echo "  >> creating destination directory $(PKGREL)"
	@if [ ! -d $(PKGREL) ]; \
	then \
		mkdir -p $(PKGREL); \
	fi

	@echo "  >> setting directory permissions for $(PKGREL)"
	@if [ ! -w $(PKGREL) ]; \
	then \
		chmod 755 $(PKGREL); \
	fi

	@echo "Packaging  $(APPSRC)/$(APPNAME) on host $(ROKU_DEV_TARGET)"
	@if [ "$(HTTPSTATUS)" == " 401" ]; \
	then \
		read -p "Password: " REPLY ; echo $$REPLY | xargs -i curl --user $(USERPASS) --digest -s -S -Fmysubmit=Package -Fapp_name=$(APPNAME)/$(VERSION) -Fpasswd={} -Fpkg_time=`expr \`date +%s\` \* 1000` "http://$(ROKU_DEV_TARGET)/plugin_package" | grep '^<tr><td><font face="Courier"><a' | sed 's/.*href=\"\([^\"]*\)\".*/\1/' | sed 's#pkgs//##' | xargs -i curl --user $(USERPASS) --digest -s -S -o $(PKGREL)/$(APPNAME)_`date +%F-%T`.pkg http://$(ROKU_DEV_TARGET)/pkgs/{} ; \
	else \
		read -p "Password: " REPLY ; echo $$REPLY | xargs -i curl -s -S -Fmysubmit=Package -Fapp_name=$(APPNAME)/$(VERSION) -Fpasswd={} -Fpkg_time=`expr \`date +%s\` \* 1000` "http://$(ROKU_DEV_TARGET)/plugin_package" | grep '^<tr><td><font face="Courier"><a' | sed 's/.*href=\"\([^\"]*\)\".*/\1/' | sed 's#pkgs//##' | xargs -i curl -s -S -o $(PKGREL)/$(APPNAME)_`date +%F-%T`.pkg http://$(ROKU_DEV_TARGET)/pkgs/{} ; \
	fi

	@echo "*** Package  $(APPNAME) complete ***"

remove:
	@echo "Removing $(APPNAME) from host $(ROKU_DEV_TARGET)"
	@if [ "$(HTTPSTATUS)" == " 401" ]; \
	then \
		curl --user $(USERPASS) --digest -s -S -F "mysubmit=Delete" -F "archive=" -F "passwd=" http://$(ROKU_DEV_TARGET)/plugin_install | grep "<font color" | sed "s/<font color=\"red\">//" | sed "s[</font>[[" ; \
	else \
		curl -s -S -F "mysubmit=Delete" -F "archive=" -F "passwd=" http://$(ROKU_DEV_TARGET)/plugin_install | grep "<font color" | sed "s/<font color=\"red\">//" | sed "s[</font>[[" ; \
	fi

install_native: $(APPNAME)
	@echo "Installing $(APPNAME) to native."
	@mkdir -p $(NATIVEDEVREL)
	@cp $(ZIPREL)/$(APPNAME).zip  $(NATIVEDEVPKG)
	@$(NATIVETICKLER)

remove_native:
	@echo "Removing $(APPNAME) from native."
	@rm $(NATIVEDEVPKG)
	@$(NATIVETICKLER)

APPS_JPG_ART=`\find . -name "*.jpg"`

art-jpg-opt:
	p4 edit $(APPS_JPG_ART)
	for i in $(APPS_JPG_ART); \
	do \
		TMPJ=`mktemp` || return 1; \
		echo "optimizing $$i"; \
		(jpegtran -copy none -optimize -outfile $$TMPJ $$i && mv -f $$TMPJ $$i &); \
	done
	wait
	p4 revert -a $(APPS_JPG_ART)

APPS_PNG_ART=`\find . -name "*.png"`

art-png-opt:
	p4 edit $(APPS_PNG_ART)
	for i in $(APPS_PNG_ART); \
	do \
		(optipng -o7 $$i &); \
	done
	wait
	p4 revert -a $(APPS_PNG_ART)

art-opt: art-png-opt art-jpg-opt

tr:
	p4 edit locale/.../translations.xml
	../../rdk/rokudev/utilities/linux/bin/maketr
	rm locale/en_US/translations.xml
	p4 revert -a locale/.../translations.xml
