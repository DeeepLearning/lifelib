"""Source module to create "Policy" space from.

.. rubric:: Space Params

Attributes:
    PolicyID: Policy ID

.. rubric:: Refs

Attributes:
    PolicyData: Input.PolicyData
    ProductSpec: Input.ProductSpec
    LifeTable: LifeTable
"""


# Policy Attributes

policy_attrs = ['Product',
                'PolicyType',
                'Gen',
                'Channel',
                'Sex',
                'Duration',
                'IssueAge',
                # 'WholeTermPaymentFlag',
                # 'PremTerm',
                # 'PremMode',
                'PremFreq',
                # 'WholeLifeFlag',
                'PolicyTerm',
                # 'MaxTerm',
                'PolicyCount',
                'SumAssured']
                # 'GrossPremMult']


def IntRate(RateBasis):
    """Interest Rate"""

    if RateBasis == 'PREM':
        int_rate = ProductSpec.IntRatePrem
    elif RateBasis == 'VAL':
        int_rate = ProductSpec.IntRateVal
    else:
        raise ValueError('invalid RateBasis')

    result = int_rate.match(Product, PolicyType, Gen).value

    if result is not None:
        return result
    else:
        raise ValueError('invalid RateBais')

def TableID(RateBasis):
    """Mortality Table ID"""

    if RateBasis == 'PREM':
        mort_table = ProductSpec.MortTablePrem
    elif RateBasis == 'VAL':
        mort_table = ProductSpec.MortTableVal
    else:
        raise ValueError('invalid RateBasis')

    result = mort_table.match(Product, PolicyType, Gen).value

    if result is not None:
        return result
    else:
        raise ValueError('invalid RateBais')


def LoadAcqSA():
    """Acquisition Loading per Sum Assured"""
    param1 = ProductSpec.LoadAcqSAParam1(Product) #, PolicyType(), Gen)
    param2 = ProductSpec.LoadAcqSAParam2(Product) #, PolicyType(), Gen)

    return param1 + param2 * min(PolicyTerm / 10, 1)

def LoadMaintGP():
    """Maintenance Loading per Gross Premium"""

    if ProductSpec.LoadMaintGPParam1(Product) is not None:
        return ProductSpec.LoadMaintGPParam1(Product)

    elif ProductSpec.LoadMaintGPParam2(Product) is not None:
        param = ProductSpec.LoadMaintGPParam2(Product)
        return (param + min(10, PolicyTerm)) / 100

    else:
        raise ValueError('LoadMaintGP parameters not found')


def LoadMaintPremWaiverGP():
    """Maintenance Loading per Gross Premium for Premium Waiver"""

    if PremTerm < 5:
        return 0.0005
    elif PremTerm < 10:
        return 0.001
    else:
        return 0.002

def LoadMaintSA():
    """Maintenance Loading per Sum Assured during Premium Payment"""

    result = ProductSpec.LoadMaintSA.match(Product, PolicyType, Gen).value

    if result is not None:
        return result
    else:
        raise ValueError('lookup failed')

def LoadMaintSA2():
    """Maintenance Loading per Sum Assured after Premium Payment"""

    result = ProductSpec.LoadMaintSA2.match(Product, PolicyType, Gen).value

    if result is not None:
        return result
    else:
        raise ValueError('lookup failed')

def InitSurrCharge():
    """Initial Surrender Charge Rate"""

    param1 = ProductSpec.SurrChargeParam1.match(Product, PolicyType, Gen).value
    param2 = ProductSpec.SurrChargeParam2.match(Product, PolicyType, Gen).value

    if param1 is None or param2 is None:
        raise ValueError('SurrChargeParam not found')

    return param1 + param2 * min(PolicyTerm / 10, 1)


def NetPremRate(basis):
    """Net Premium Rate"""

    gamma2 = LoadMaintSA2
    comf = LifeTable[Sex, IntRate(basis), TableID(basis)]

    if Product == 1 or Product == 2:
        return (comf.Axn(x, n) + gamma2 * comf.AnnDuenx(x, n - m, 1, m)) / comf.AnnDuenx(x, n)

    elif Product == 3:
        return (comf.Axn(x, n) + gamma2 * comf.AnnDuenx(x, n - m, 1, m)) / comf.AnnDuenx(x, n)

    else:
        raise ValueError('invalid product')


def GrossPremRate():
    """Gross Premium Rate per Sum Assured per payment"""

    alpha = LoadAcqSA
    beta = LoadMaintGP
    gamma = LoadMaintSA
    gamma2 = LoadMaintSA2
    delta = LoadMaintPremWaiverGP

    comf = LifeTable[Sex, IntRate('PREM'), TableID('PREM')]

    if Product == 1 or Product == 2:
        return (comf.Axn(x, n) + alpha + gamma * comf.AnnDuenx(x, n, PremFreq)
                + gamma2 * comf.AnnDuenx(x, n - m, 1, m)) / (1 - beta - delta) / PremFreq / comf.AnnDuenx(x, m, PremFreq)

    elif Product == 3:
        return (comf.Exn(x, n) + comf.Axn(x, n) + alpha + gamma * comf.AnnDuenx(x, n, PremFreq)
                + gamma2 * comf.AnnDuenx(x, n - m, 1, m)) / (1 - beta - delta) / PremFreq / comf.AnnDuenx(x, m, PremFreq)
    else:
        raise ValueError('invalid product')


def AnnualizedPremRate():
    """Annualized Premium Rate per Sum Assured"""
    return GrossPremRate * (1 / 10 if PremFreq == 0 else PremFreq)


def GrossPremTable():
    """Gross premium table"""
    return None

def NLPReserveRate(basis, t):
    """Net level premium reserve rate"""

    gamma2 = LoadMaintSA2

    lt = LifeTable[Sex, IntRate(basis), TableID(basis)]

    if t <= m:
        return lt.Axn(x + t, n - t) + gamma2 * lt.AnnDuenx(x + t, n - m, 1, m - t) \
                - NetPremRate(basis) * lt.AnnDuenx(x + t, m - t)
    else:
        return lt.Axn(x + t, n - t) + gamma2 * lt.AnnDuenx(x + t, n - m, 1, m - t)


def ReserveRate():
    """Valuation Reserve Rate per Sum Assured"""
    return None

def SurrCharge(t):
    """Surrender Charge Rate per Sum Assured"""
    return InitSurrCharge * max((min(m, 10) - t) / min(m, 10), 0)

def CashValueRate(t):
    """Cash Value Rate per Sum Assured"""
    return max(NLPReserveRate('PREM', t) - SurrCharge(t), 0)

def UnearnedPremRate():
    """Unearned Premium Rate"""
    return None


