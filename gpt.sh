#!/bin/sh
java -cp "../modules/*:../lib/*" -Dsnap.mainClass=org.esa.snap.core.gpf.main.GPT -Dsnap.home="../" -Xmx2400M org.esa.snap.runtime.Launcher "$@"
