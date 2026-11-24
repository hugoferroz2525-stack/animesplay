"""Perfil local. As chaves são páginas estáveis do Bakashi."""
def initialize(db):
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS library (
            seq INTEGER PRIMARY KEY, section TEXT NOT NULL, url TEXT NOT NULL,
            title TEXT NOT NULL, art TEXT NOT NULL, UNIQUE(section,url))""")


def save(db, section, url, title, art):
    with db:
        db.execute('INSERT OR REPLACE INTO library(section,url,title,art) VALUES (?,?,?,?)',
                   (section, url, title, art))
        if section == 'recent':
            db.execute("""DELETE FROM library WHERE section='recent' AND seq NOT IN
                          (SELECT seq FROM library WHERE section='recent' ORDER BY seq DESC LIMIT 50)""")


def contents(db, section):
    return db.execute('SELECT url,title,art FROM library WHERE section=? ORDER BY seq DESC',
                      (section,)).fetchall()


def remove(db, url):
    with db:
        db.execute("DELETE FROM library WHERE section='favorites' AND url=?", (url,))
