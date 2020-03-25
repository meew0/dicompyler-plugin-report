# Report Plugin for dicompyler

This is a very simple plugin for [dicompyler](https://github.com/bastula/dicompyler) that generates a one-page PDF report of a loaded RT plan, including patient metadata, a DVH, and a table of structure dose metrics. Most treatment planning software can already do this with much more configurability and detail, but this plugin might be helpful if you can't use your treatment planning software for this purpose for any reason. (In my case, the planning software intermittently refused to load report templates) Perhaps this plugin could prove useful to somebody else with a similar problem.

To use it, clone this repo as a separate folder into your dicompyler [plugins directory](https://github.com/bastula/dicompyler/wiki/PluginDevelopmentGuide#plugin-file-structure). Open up dicompyler and load the DICOM-RT data you want to process, select the structures you want to be present in the report, then go to File -> Export -> Plan Report as PDF and choose a file name. Ideally, this should result in a "Report created successfully" message.

I have only tested this with DICOM files exported from one planning software, but in theory it should work for other platforms as well. The generated reports look like this:
![report](https://i.imgur.com/mGm6ckL.png)
