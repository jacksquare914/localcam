def parse(s):
    i=0; 
    def rd():
        nonlocal i
        while i<len(s) and s[i] in ' \t\r\n': i+=1
        if s[i]=='(':
            i+=1; out=[]
            while True:
                while i<len(s) and s[i] in ' \t\r\n': i+=1
                if s[i]==')': i+=1; return out
                out.append(rd())
        if s[i]=='"':
            i+=1; b=[]
            while s[i]!='"':
                if s[i]=='\\': i+=1
                b.append(s[i]); i+=1
            i+=1; return '"'+''.join(b)
        b=[]
        while i<len(s) and s[i] not in ' \t\r\n()': b.append(s[i]); i+=1
        return ''.join(b)
    return rd()
def find(node,tag):
    return [x for x in node if isinstance(x,list) and x and x[0]==tag]
def val(node,tag,idx=1):
    f=find(node,tag)
    return f[0][idx] if f else None
def unq(x): return x[1:] if isinstance(x,str) and x.startswith('"') else x
