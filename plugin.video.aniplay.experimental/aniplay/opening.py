import re


def seconds(value):
    found = re.fullmatch(r'([0-9]{1,3}):([0-5][0-9])',value.strip())
    if not found:
        raise ValueError('Use minutos:segundos.')
    return 60*int(found[1])+int(found[2])


def saved(db,url):
    db.execute('CREATE TABLE IF NOT EXISTS opening (url TEXT PRIMARY KEY, start INTEGER, end INTEGER)')
    return db.execute('SELECT start,end FROM opening WHERE url=?',(url,)).fetchone()


def configure(db,url):
    import xbmcgui
    from aniplay.flix_ui import notification
    dialog = xbmcgui.Dialog()
    existing = saved(db,url)
    if existing:
        action = dialog.select('Abertura deste episódio',['Ajustar intervalo','Restaurar marcação automática'])
        if action < 0:
            return
        if action == 1:
            with db:
                db.execute('DELETE FROM opening WHERE url=?',(url,))
            return
    start,end = existing or (0,0)
    values = []
    for label,t in [('Início',start),('Fim',end)]:
        v = dialog.input(label+' da abertura (min:seg)',defaultt='%d:%02d' % divmod(t,60))
        if not v:
            return
        try:
            values.append(seconds(v))
        except ValueError as exc:
            notification(str(exc),icon='skip')
            return
    if values[1]<=values[0]:
        notification('O fim precisa ser posterior ao início.',icon='skip')
        return
    with db:
        db.execute('INSERT OR REPLACE INTO opening VALUES (?,?,?)',(url,*values))
    notification('Abertura salva para este episódio.',icon='skip')
