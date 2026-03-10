import lionscliapp as app

from . import gui

app.declare_app("mtr", "0.1.0")
app.describe_app("Record keypress timing signals with millisecond precision and export as JSON.")

app.declare_projectdir(".mtr")

app.declare_key("path.output", "~")
app.describe_key("path.output", "Default directory shown in the Export Timings dialog.")

app.declare_key("json.indent.timings", 2)
app.describe_key("json.indent.timings", "Indentation level for exported timing JSON (0 = compact).")

app.declare_cmd("", gui.launch)

app.main()
