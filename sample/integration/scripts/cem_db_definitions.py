from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
Base = declarative_base()


class allowBuilds(Base):
    __tablename__ = 'allowBuilds'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    steps = Column(Float)
    allowBuilds = Column(Float)

class BatteryChargeCap(Base):
    __tablename__ = 'BatteryChargeCap'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    y = Column(Integer)
    r = Column(Float)
    steps = Column(Float)
    hr = Column(Integer)
    BatteryChargeCap = Column(Float)

class BatteryEfficiency(Base):
    __tablename__ = 'BatteryEfficiency'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    BatteryEfficiency = Column(Float)

class CapacityCredit(Base):
    __tablename__ = 'CapacityCredit'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    y = Column(Integer)
    r = Column(Float)
    steps = Column(Float)
    hr = Column(Integer)
    CapacityCredit = Column(Float)

class CapCost(Base):
    __tablename__ = 'CapCost'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    pt = Column(Float)
    y = Column(Integer)
    steps = Column(Float)
    CapCost = Column(Float)

class CapCost_y0(Base):
    __tablename__ = 'CapCost_y0'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    pt = Column(Float)
    steps = Column(Float)
    CapCost_y0 = Column(Float)

class Dayweights(Base):
    __tablename__ = 'Dayweights'
    id = Column(Integer, primary_key=True)
    hr = Column(Integer)
    Dayweights = Column(Float)

class FOMCost(Base):
    __tablename__ = 'FOMCost'
    id = Column(Integer, primary_key=True)
    r = Column(Integer)
    pt = Column(Float)
    steps = Column(Float)
    FOMCost = Column(Float)

class GenSet(Base):
    __tablename__ = 'GenSet'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    y = Column(Integer)
    r = Column(Float)
    steps = Column(Float)
    hr = Column(Integer)
    SupplyCurve = Column(Float)

class HourstoBuy(Base):
    __tablename__ = 'HourstoBuy'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    HourstoBuy = Column(Float)

class Hr_weights(Base):
    __tablename__ = 'Hr_weights'
    id = Column(Integer, primary_key=True)
    hr = Column(Integer)
    Hr_weights = Column(Integer)

class HydroCapFactor(Base):
    __tablename__ = 'HydroCapFactor'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    day = Column(Float)
    HydroCapFactor = Column(Float)

class Idaytq(Base):
    __tablename__ = 'Idaytq'
    id = Column(Integer, primary_key=True)
    day = Column(Float)
    Idaytq = Column(Float)

class LearningRate(Base):
    __tablename__ = 'LearningRate'
    id = Column(Integer, primary_key=True)
    pt = Column(Integer)
    LearningRate = Column(Float)

class Load(Base):
    __tablename__ = 'Load'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    y = Column(Integer)
    hr = Column(Integer)
    Load = Column(Float)

class Map_day_s(Base):
    __tablename__ = 'Map_day_s'
    id = Column(Integer, primary_key=True)
    day = Column(Integer)
    s = Column(Float)

class Map_hr_d(Base):
    __tablename__ = 'Map_hr_d'
    id = Column(Integer, primary_key=True)
    hr = Column(Integer)
    day = Column(Integer)

class Map_hr_s(Base):
    __tablename__ = 'Map_hr_s'
    id = Column(Integer, primary_key=True)
    hr = Column(Integer)
    s = Column(Float)

class ProcurementSet(Base):
    __tablename__ = 'ProcurementSet'
    id = Column(Integer, primary_key=True)
    restypes = Column(Integer)
    pt = Column(Float)
    y = Column(Integer)
    r = Column(Float)
    steps = Column(Float)
    hr = Column(Integer)
    SupplyCurve = Column(Float)

class ptiUpperSet(Base):
    __tablename__ = 'ptiUpperSet'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    y = Column(Integer)
    r = Column(Float)
    steps = Column(Float)
    hr = Column(Integer)
    SolWindCapFactor = Column(Float)

class RampDown_Cost(Base):
    __tablename__ = 'RampDown_Cost'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    RampDown_Cost = Column(Float)

class RampRate(Base):
    __tablename__ = 'RampRate'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    RampRate = Column(Float)

class RampSet(Base):
    __tablename__ = 'RampSet'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    y = Column(Integer)
    r = Column(Float)
    steps = Column(Float)
    hr = Column(Integer)
    SupplyPrice = Column(Float)

class RampUp_Cost(Base):
    __tablename__ = 'RampUp_Cost'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    RampUp_Cost = Column(Float)

class RegReservesCost(Base):
    __tablename__ = 'RegReservesCost'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    RegReservesCost = Column(Float)

class ReserveMarginReq(Base):
    __tablename__ = 'ReserveMarginReq'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    y = Column(Integer)
    hr = Column(Integer)
    ReserveMarginReq = Column(Float)

class ResTechUpperBound(Base):
    __tablename__ = 'ResTechUpperBound'
    id = Column(Integer, primary_key=True)
    restype = Column(Float)
    pt = Column(Float)
    ResTechUpperBound = Column(Float)

class RetSet(Base):
    __tablename__ = 'RetSet'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    y = Column(Integer)
    r = Column(Float)
    steps = Column(Float)
    RetSet = Column(Float)

class SupplyCurve(Base):
    __tablename__ = 'SupplyCurve'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    s = Column(Float)
    pt = Column(Float)
    steps = Column(Float)
    y = Column(Integer)
    SupplyCurve = Column(Float)

class SupplyCurveMonths(Base):
    __tablename__ = 'SupplyCurveMonths'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    y = Column(Integer)
    r = Column(Float)
    s = Column(Float)
    SupplyCurveMonths = Column(Float)

class SupplyCurve_learning(Base):
    __tablename__ = 'SupplyCurve_learning'
    id = Column(Integer, primary_key=True)
    pt = Column(Float)
    SupplyCurve_learning = Column(Float)

class SupplyPrice(Base):
    __tablename__ = 'SupplyPrice'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    s = Column(Float)
    pt = Column(Float)
    steps = Column(Float)
    y = Column(Integer)
    SupplyPrice = Column(Float)

class TradeCanSet(Base):
    __tablename__ = 'TradeCanSet'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    r1 = Column(Float)
    y = Column(Integer)
    CSteps = Column(Float)
    hr = Column(Integer)
    TranLineLimitCan = Column(Float)

class TradeSet(Base):
    __tablename__ = 'TradeSet'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    r1 = Column(Float)
    y = Column(Integer)
    hr = Column(Integer)
    TranLimit = Column(Float)

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
    r1 = Column(Float)
    CSteps = Column(Float)
    y = Column(Integer)
    hr = Column(Integer)
    TranLimitCan = Column(Float)

class TranLineLimitCan(Base):
    __tablename__ = 'TranLineLimitCan'
    id = Column(Integer, primary_key=True)
    r = Column(Float)
    r1 = Column(Float)
    y = Column(Integer)
    hr = Column(Integer)
    TranLineLimitCan = Column(Float)

class year_weights(Base):
    __tablename__ = 'year_weights'
    id = Column(Integer, primary_key=True)
    y = Column(Integer)
    year_weights = Column(Integer)
