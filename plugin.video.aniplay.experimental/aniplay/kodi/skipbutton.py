"""Botão "Pular abertura" exibido sobre o vídeo."""
import xbmcgui

BUTTON = 10
DISMISS = (9, 10, 92)  # parent dir, previous menu, nav back


class SkipButton(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.label = kwargs.get('label', 'Pular abertura')
        self.on_skip = kwargs.get('on_skip')

    def onInit(self):
        self.getControl(BUTTON).setLabel(self.label)
        self.setFocusId(BUTTON)

    def onClick(self, control):
        if control == BUTTON:
            callback = self.on_skip
            self.close()
            if callback:
                callback()

    def onAction(self, action):
        if action.getId() in DISMISS:
            self.close()
            return
        xbmcgui.WindowXMLDialog.onAction(self, action)
