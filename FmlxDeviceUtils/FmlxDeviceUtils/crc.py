import ctypes

def crc16(dataList):
    crc = 0xffff
    for data in dataList:
        x = ctypes.c_uint16(crc).value >> 8 ^ data
        x^=x>>4
        crc = (crc << 8) ^ ( ctypes.c_uint16( x << 12 ).value ) ^ ( ctypes.c_uint16( x << 5 ).value ) ^ ( ctypes.c_uint16(x).value )
    return ctypes.c_uint16(crc).value

if __name__ == "__main__":
    a = [12,45,69,212]
    print(crc16(a)) # should be printed 30373