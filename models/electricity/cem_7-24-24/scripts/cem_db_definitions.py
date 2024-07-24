from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
Base = declarative_base()


class allowBuilds(Base):
    __tablename__ = 'allowBuilds'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    steps = Column(Float)
    allowBuilds = Column(Float)

class BatteryEfficiency(Base):
    __tablename__ = 'BatteryEfficiency'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    BatteryEfficiency = Column(Float)

class CapCost(Base):
    __tablename__ = 'CapCost'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    pt = Column(Integer)
    y = Column(Integer)
    steps = Column(Float)
    CapCost = Column(Float)

class CapCost_y0(Base):
    __tablename__ = 'CapCost_y0'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    pt = Column(Integer)
    steps = Column(Float)
    CapCost_y0 = Column(Float)

class FOMCost(Base):
    __tablename__ = 'FOMCost'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    pt = Column(Integer)
    steps = Column(Float)
    FOMCost = Column(Float)

class H2Price(Base):
    __tablename__ = 'H2Price'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    s = Column(Integer)
    pt = Column(Integer)
    steps = Column(Integer)
    y = Column(Integer)
    H2Price = Column(Float)

class H2Supply(Base):
    __tablename__ = 'H2Supply'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    s = Column(Integer)
    pt = Column(Integer)
    steps = Column(Integer)
    y = Column(Integer)
    H2Supply = Column(Float)

class HourstoBuy(Base):
    __tablename__ = 'HourstoBuy'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    HourstoBuy = Column(Float)

class HydroCapFactor(Base):
    __tablename__ = 'HydroCapFactor'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    s = Column(Integer)
    HydroCapFactor = Column(Float)

class LearningRate(Base):
    __tablename__ = 'LearningRate'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    LearningRate = Column(Float)

class Load(Base):
    __tablename__ = 'Load'
    id = Column(Integer, primary_key=True)
    y = Column(Integer)
    hr = Column(Integer)
    r1 = Column(Float)
    r2 = Column(Float)
    r3 = Column(Float)
    r4 = Column(Float)
    r5 = Column(Float)
    r6 = Column(Float)
    r7 = Column(Float)
    r8 = Column(Float)
    r9 = Column(Float)
    r10 = Column(Float)
    r11 = Column(Float)
    r12 = Column(Float)
    r13 = Column(Float)
    r14 = Column(Float)
    r15 = Column(Float)
    r16 = Column(Float)
    r17 = Column(Float)
    r18 = Column(Float)
    r19 = Column(Float)
    r20 = Column(Float)
    r21 = Column(Float)
    r22 = Column(Float)
    r23 = Column(Float)
    r24 = Column(Float)
    r25 = Column(Float)

class ptiUpperSet(Base):
    __tablename__ = 'ptiUpperSet'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    r = Column(Integer)
    steps = Column(Integer)
    hr = Column(Integer)
    SolWindCapFactor = Column(Float)

class RampDown_Cost(Base):
    __tablename__ = 'RampDown_Cost'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    RampDown_Cost = Column(Float)

class RampRate(Base):
    __tablename__ = 'RampRate'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    RampRate = Column(Float)

class RampUp_Cost(Base):
    __tablename__ = 'RampUp_Cost'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    RampUp_Cost = Column(Float)

class RegReservesCost(Base):
    __tablename__ = 'RegReservesCost'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    RegReservesCost = Column(Float)

class ReserveMargin(Base):
    __tablename__ = 'ReserveMargin'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    ReserveMargin = Column(Float)

class ResTechUpperBound(Base):
    __tablename__ = 'ResTechUpperBound'
    id = Column(Integer, primary_key=True)
    restype = Column(Float)
    pt = Column(Integer)
    ResTechUpperBound = Column(Float)

class RetSet(Base):
    __tablename__ = 'RetSet'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    y = Column(Integer)
    r = Column(Float)
    steps = Column(Float)
    RetSet = Column(Float)

class SupplyCurve(Base):
    __tablename__ = 'SupplyCurve'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    s = Column(Integer)
    pt = Column(Integer)
    steps = Column(Integer)
    y = Column(Integer)
    SupplyCurve = Column(Float)

class SupplyCurve_learning(Base):
    __tablename__ = 'SupplyCurve_learning'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    SupplyCurve_learning = Column(Float)

class SupplyPrice(Base):
    __tablename__ = 'SupplyPrice'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    s = Column(Integer)
    pt = Column(Integer)
    steps = Column(Integer)
    y = Column(Integer)
    SupplyPrice = Column(Float)

class TranCost(Base):
    __tablename__ = 'TranCost'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    r1 = Column(Float)
    y = Column(Integer)
    TranCost = Column(Float)

class TranCostCan(Base):
    __tablename__ = 'TranCostCan'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    r1 = Column(Float)
    CSteps = Column(Float)
    y = Column(Integer)
    TranCostCan = Column(Float)

class TranLimit(Base):
    __tablename__ = 'TranLimit'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    r1 = Column(Float)
    s = Column(Float)
    y = Column(Integer)
    TranLimit = Column(Float)

class TranLimitCan(Base):
    __tablename__ = 'TranLimitCan'
    id = Column(Integer, primary_key=True)
    r1 = Column(Integer)
    CSteps = Column(Integer)
    y = Column(Integer)
    s = Column(Integer)
    TranLimitCan = Column(Float)

class TranLineLimitCan(Base):
    __tablename__ = 'TranLineLimitCan'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    r1 = Column(Integer)
    y = Column(Integer)
    s = Column(Integer)
    TranLineLimitCan = Column(Float)
