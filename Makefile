include config/Makefile.config

targets = pyctf parsemarks avghc StockwellDs filterDs projDs thresholdDetect

all:
	for x in $(targets) ; do \
		$(MAKE) -C $$x $@ || exit ;\
	done

install: all
	for x in $(targets) ; do \
		$(MAKE) -C $$x $@ || exit ;\
	done

clean: clean-x
