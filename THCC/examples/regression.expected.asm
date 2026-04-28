  0: loadn 3
  1: store 83
  2: loadn 1
  3: store 84
  4: loadn 3
  5: store 85
  6: loadn 2
  7: store 86
  8: loadn 5
  9: store 87
 10: loadn 3
 11: store 88
 12: loadn 7
 13: store 89
 14: loadm 84
 15: addm 86
 16: addm 88
 17: store 90
 18: loadm 85
 19: addm 87
 20: addm 89
 21: store 91
 22: loadm 84
 23: mulm 85
 24: store 98
 25: loadm 86
 26: mulm 87
 27: store 99
 28: loadm 98
 29: addm 99
 30: store 98
 31: loadm 88
 32: mulm 89
 33: store 99
 34: loadm 98
 35: addm 99
 36: store 92
 37: loadm 84
 38: mulm 84
 39: store 98
 40: loadm 86
 41: mulm 86
 42: store 99
 43: loadm 98
 44: addm 99
 45: store 98
 46: loadm 88
 47: mulm 88
 48: store 99
 49: loadm 98
 50: addm 99
 51: store 93
 52: loadm 83
 53: mulm 92
 54: store 98
 55: loadm 90
 56: mulm 91
 57: store 99
 58: loadm 98
 59: subm 99
 60: store 94
 61: loadm 83
 62: mulm 93
 63: store 98
 64: loadm 90
 65: mulm 90
 66: store 99
 67: loadm 98
 68: subm 99
 69: store 95
 70: loadm 94
 71: divm 95
 72: store 96
 73: loadm 91
 74: store 98
 75: loadm 96
 76: mulm 90
 77: store 99
 78: loadm 98
 79: subm 99
 80: divm 83
 81: store 97
 82: halt

; variables:
; n -> RAM[83]
; x0 -> RAM[84]
; y0 -> RAM[85]
; x1 -> RAM[86]
; y1 -> RAM[87]
; x2 -> RAM[88]
; y2 -> RAM[89]
; sum_x -> RAM[90]
; sum_y -> RAM[91]
; sum_xy -> RAM[92]
; sum_xx -> RAM[93]
; w_num -> RAM[94]
; w_den -> RAM[95]
; w -> RAM[96]
; b -> RAM[97]
