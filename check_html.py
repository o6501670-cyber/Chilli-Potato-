from html.parser import HTMLParser

class TagParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.void_elements = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
        
    def handle_starttag(self, tag, attrs):
        if tag not in self.void_elements:
            self.stack.append((tag, self.getpos()))
            
    def handle_endtag(self, tag):
        if tag not in self.void_elements:
            if not self.stack:
                print(f'Unmatched end tag </{tag}> at {self.getpos()}')
            elif self.stack[-1][0] == tag:
                self.stack.pop()
            else:
                print(f'Mismatched tag </{tag}> at {self.getpos()}, expected </{self.stack[-1][0]}> (opened at {self.stack[-1][1]})')
                
    def close(self):
        super().close()
        for tag, pos in self.stack:
            print(f'Unclosed tag <{tag}> at {pos}')

with open('frontend/src/app/finance/finance.html', encoding='utf-8') as f:
    parser = TagParser()
    parser.feed(f.read())
    parser.close()
