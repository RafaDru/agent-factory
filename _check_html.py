with open('src/dashboard/index.html', encoding='utf-8') as f:
    content = f.read()
line = [l for l in content.split('\n') if 'btnRefresh' in l][0]
print('Line repr:', repr(line))
print('Has exact anchor:', '<button class="btn" id="btnRefresh" onclick="refreshData()" title="Refresh">' in content)
print('Anchor end:', repr('<button class="btn" id="btnRefresh" onclick="refreshData()" title="Refresh">' in line))
