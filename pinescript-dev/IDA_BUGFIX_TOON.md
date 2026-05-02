# TOON — IDA Bug Fix Instruction (Verified)

## ROLE
You are a PineScript v6 engineer. You will receive the full source of
`Institutional Delta Architecture (IDA)` (~696 lines).
Apply EXACTLY the 4 fixes below. Touch nothing else.

## RULES
- No renames, no reordering, no new comments, no refactoring outside bug scope.
- No changes to `request.security` calls, inputs, plots, drawing engine, or CSDCE pipeline.
- Preserve existing whitespace (4-space indent inside functions).
- Output the COMPLETE modified file.

---

## BUG 1 — f_getZone uses uniform sixths; bucket math uses Fibonacci edges

### WHAT IS WRONG
Line 89–90 define Fibonacci boundaries:
```
ZONE_BOTTOM = array.from( 0.0, 23.6, 38.2, 50.0, 61.8, 78.6)
ZONE_TOP    = array.from(23.6, 38.2, 50.0, 61.8, 78.6, 100.0)
```
Lines 105–119 (`f_getZone`) classify into equal sixths (0–16.666, 16.666–33.333 …).
`f_getBucket` and `f_bucketCenter` then index into `ZONE_BOTTOM`/`ZONE_TOP` using
the zone index returned by `f_getZone`. The ranges don't match.
Result: every gravity attractor is computed against the wrong sub-range.

### EXACT CURRENT CODE (lines 105–119)
```pinescript
f_getZone(float v) =>
    int z = -1
    if v >= 0.0   and v <  16.666 
        z := 0
    else if v >= 16.666  and v <  33.333  
        z := 1
    else if v >= 33.333  and v <  49.999  
        z := 2
    else if v >= 49.999  and v <  66.666  
        z := 3
    else if v >= 66.666  and v <  83.333  
        z := 4
    else if v >= 83.333  and v <= 99.999 
        z := 5
    z
```

### REPLACE WITH
```pinescript
f_getZone(float v) =>
    int z = -1
    if v >= 0.0 and v < 23.6
        z := 0
    else if v >= 23.6 and v < 38.2
        z := 1
    else if v >= 38.2 and v < 50.0
        z := 2
    else if v >= 50.0 and v < 61.8
        z := 3
    else if v >= 61.8 and v < 78.6
        z := 4
    else if v >= 78.6 and v <= 100.0
        z := 5
    z
```

### WHY THIS IS CORRECT
For any input `v`, the returned `zi` now satisfies
`ZONE_BOTTOM[zi] <= v < ZONE_TOP[zi]`, which is what `f_getBucket` assumes.

---

## BUG 2 — Division by zero in `pc` and its downstream consumers

### WHAT IS WRONG
Line 211:
```pinescript
pc = ((math.max((FC -minLevel),guard) - math.max((FO - minLevel), guard)))*100/(math.max(FC[1], FH) - minLevel )
```
Denominator `(math.max(FC[1], FH) - minLevel)` is zero when high == previous close == current low.
`guard` only protects numerator terms.

Additionally, lines 214 and 218 divide `rsc/pc`. If `pc` is zero after the denominator fix
(numerator evaluates to zero), those lines also divide by zero.

### EXACT CURRENT CODE (lines 211, 214, 218)
```pinescript
pc = ((math.max((FC -minLevel),guard) - math.max((FO - minLevel), guard)))*100/(math.max(FC[1], FH) - minLevel )
...
ur = math.sum( rsc >= 0 ?  rsc/pc : 0 , candle_mrk_len)
...
dr = math.sum(rsc < 0 ?  (rsc/pc) : 0  , candle_mrk_len)
```

### REPLACE LINE 211 WITH
```pinescript
pc = ((math.max((FC -minLevel),guard) - math.max((FO - minLevel), guard)))*100/ math.max((math.max(FC[1], FH) - minLevel), guard)
```

### REPLACE LINE 214 WITH
```pinescript
ur = math.sum( rsc >= 0 and pc != 0 ?  rsc/pc : 0 , candle_mrk_len)
```

### REPLACE LINE 218 WITH
```pinescript
dr = math.sum(rsc < 0 and pc != 0 ?  (rsc/pc) : 0  , candle_mrk_len)
```

### WHY THIS IS CORRECT
Denominator is now floored at `guard` (= `syminfo.mintick`, always > 0).
Downstream divisions are gated on `pc != 0` so even if the numerator
produces a legitimate zero, no NaN propagates into `ur`/`dr`.

---

## BUG 3 — ur/dr ratio is inverted (count/sum instead of sum/count)

### WHAT IS WRONG
Lines 214–220:
```pinescript
ur = math.sum( rsc >= 0 ?  rsc/pc : 0 , candle_mrk_len)   // sum of ratios
ur_ = math.sum( rsc >= 0 ?  1 : 0 , candle_mrk_len )      // count
ur := (ur == 0 ? 0 : ur_/ur )                              // count / sum ← WRONG
```
`ur_/ur` = count / sum-of-ratios. Dimensionally inverted.
Large price moves produce small values; small moves produce large values.
Same bug on `dr`.

### EXACT CURRENT CODE (lines 216, 220)
```pinescript
ur := (ur == 0 ? 0 : ur_/ur )
...
dr := (dr == 0 ? 0 : dr_/dr )
```

### REPLACE LINE 216 WITH
```pinescript
ur := (ur_ == 0 ? 0 : ur / ur_ )
```

### REPLACE LINE 220 WITH
```pinescript
dr := (dr_ == 0 ? 0 : dr / dr_ )
```

### WHY THIS IS CORRECT
Average response = sum / count = `ur / ur_`.
Zero-guard is now on `ur_` (count), not `ur` (sum).
A zero sum with nonzero count is a valid result (net-zero response).
A zero count is the actual division hazard.

---

## BUG 4 — Spearman rank correlation assigns duplicate ranks to tied values

### WHAT IS WRONG
Lines 432–433:
```pinescript
int rank1 = array.indexof(sorted1, val1) + 1
int rank2 = array.indexof(sorted2, val2) + 1
```
`array.indexof` returns the FIRST index. Tied values get identical ranks.
On a 15-bar window, ties are frequent in smoothed RSI and Kalman output.
This biases correlation toward zero → false divergence signals in CSDCE.

### EXACT CURRENT CODE (lines 415–439)
```pinescript
f_spearman(float src1, float src2, int length) =>
    float[] arr1 = array.new_float(length)
    float[] arr2 = array.new_float(length)
    for i = 0 to length - 1
        array.set(arr1, i, nz(src1[i]))
        array.set(arr2, i, nz(src2[i]))
    
    float[] sorted1 = array.copy(arr1)
    float[] sorted2 = array.copy(arr2)
    array.sort(sorted1)
    array.sort(sorted2)
    
    float sum_d2 = 0.0
    for i = 0 to length - 1
        float val1 = array.get(arr1, i)
        float val2 = array.get(arr2, i)
        
        int rank1 = array.indexof(sorted1, val1) + 1
        int rank2 = array.indexof(sorted2, val2) + 1
        
        float d = rank1 - rank2
        sum_d2 += d * d
        
    float spearman = 1.0 - (6.0 * sum_d2) / (length * (math.pow(length, 2) - 1))
    math.max(-1.0, math.min(1.0, spearman))
```

### REPLACE ENTIRE FUNCTION WITH
```pinescript
f_spearman(float src1, float src2, int length) =>
    float[] arr1 = array.new_float(length)
    float[] arr2 = array.new_float(length)
    for i = 0 to length - 1
        array.set(arr1, i, nz(src1[i]))
        array.set(arr2, i, nz(src2[i]))
    
    float[] sorted1 = array.copy(arr1)
    float[] sorted2 = array.copy(arr2)
    array.sort(sorted1)
    array.sort(sorted2)
    
    float sum_d2 = 0.0
    for i = 0 to length - 1
        float val1 = array.get(arr1, i)
        float val2 = array.get(arr2, i)
        
        int first1 = array.indexof(sorted1, val1)
        int last1  = array.lastindexof(sorted1, val1)
        float rank1 = (first1 + last1) / 2.0 + 1.0

        int first2 = array.indexof(sorted2, val2)
        int last2  = array.lastindexof(sorted2, val2)
        float rank2 = (first2 + last2) / 2.0 + 1.0
        
        float d = rank1 - rank2
        sum_d2 += d * d
        
    float spearman = 1.0 - (6.0 * sum_d2) / (length * (math.pow(length, 2) - 1))
    math.max(-1.0, math.min(1.0, spearman))
```

### WHY THIS IS CORRECT
Mid-rank = `(first_index + last_index) / 2.0 + 1.0`.
When no ties: `first == last`, reduces to original `indexof + 1`.
When ties: both tied values get the average of their positions.
`rank1`/`rank2` are now `float`, not `int`. `d` was already `float`.
No other type changes needed.

---

## APPLY ORDER
All 4 bugs are independent. Apply in any order.
After all patches the file must compile with zero errors on PineScript v6.
No new inputs, plots, or security calls are introduced.
