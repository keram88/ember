class DrawText:
    def __init__(self, x, y, text, font, color):
        self.x = x
        self.y = y
        self.y1 = y
        self.y2 = y + 50
        self.text = text
        self.font = font
        self.color = color
        
    def draw(self, scrolly, canvas):
        canvas.create_text(self.x, self.y - scrolly, text=self.text, font=self.font, anchor='nw', fill = self.color)

class DrawRect:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def draw(self, scrolly, canvas):
        canvas.create_rectangle(self.x1, self.y1 - scrolly, self.x2, self.y2 - scrolly)
