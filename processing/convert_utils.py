import math

def utm_ll(E, N, zone=48, south=True):
    a=6378137.0; f=1/298.257223563; k0=0.9996; e2=f*(2-f); ep2=e2/(1-e2)
    x=E-500000.0; y=N-(10000000.0 if south else 0.0); M=y/k0
    mu=M/(a*(1-e2/4-3*e2**2/64-5*e2**3/256)); e1=(1-math.sqrt(1-e2))/(1+math.sqrt(1-e2))
    p=(mu+(3*e1/2-27*e1**3/32)*math.sin(2*mu)+(21*e1**2/16-55*e1**4/32)*math.sin(4*mu)
       +(151*e1**3/96)*math.sin(6*mu)+(1097*e1**4/512)*math.sin(8*mu))
    s=math.sin(p); c=math.cos(p); t=math.tan(p)
    C=ep2*c*c; T=t*t; Nn=a/math.sqrt(1-e2*s*s); R=a*(1-e2)/(1-e2*s*s)**1.5; D=x/(Nn*k0)
    lat=p-(Nn*t/R)*(D**2/2-(5+3*T+10*C-4*C*C-9*ep2)*D**4/24+(61+90*T+298*C+45*T*T-252*ep2-3*C*C)*D**6/720)
    lon0=math.radians((zone-1)*6-180+3)
    lon=lon0+(D-(1+2*T+C)*D**3/6+(5-2*C+28*T-3*C*C+8*ep2+24*T*T)*D**5/120)/c
    return math.degrees(lat), math.degrees(lon)

