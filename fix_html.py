t = open("src/dashboard/index.html", encoding="utf-8").read()
old_size = len(t)
if "</script>" not in t:
    t += "\n</script>\n"
if "</body>" not in t:
    t += "</body>\n"
if "</html>" not in t and t.strip().endswith("}"):
    t += "\n</html>\n"
open("src/dashboard/index.html", "w", encoding="utf-8").write(t)
print(f"Fixed: {old_size} -> {len(t)} bytes")
print(f"Has script close: {'</script>' in t}")
print(f"Has body close: {'</body>' in t}")
print(f"Has html close: {'</html>' in t}")
