"""Repository layer with typed CRUD operations."""

from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from src.storage.models import (
    MarketIndex, FundBasicInfo, FundNav, FundPerformance, FundScore,
    SectorPerformance, MacroIndicator, Portfolio, AllocationPlan,
    Holding, Transaction, Alert
)


class Repository:
    """Unified repository for all database operations."""

    def __init__(self, session: Session):
        self.session = session

    # ================================================================
    # Market Index
    # ================================================================
    def upsert_market_index(self, symbol: str, index_name: str, trade_date: date,
                            open_: float = None, high: float = None, low: float = None,
                            close: float = None, volume: float = None, amount: float = None,
                            pe_ttm: float = None, pb: float = None):
        """Insert or update a market index record."""
        existing = self.session.query(MarketIndex).filter(
            MarketIndex.symbol == symbol,
            MarketIndex.trade_date == trade_date
        ).first()
        if existing:
            if close is not None:
                existing.close = close
            if open_ is not None:
                existing.open = open_
            if high is not None:
                existing.high = high
            if low is not None:
                existing.low = low
            if volume is not None:
                existing.volume = volume
            if amount is not None:
                existing.amount = amount
            if pe_ttm is not None:
                existing.pe_ttm = pe_ttm
            if pb is not None:
                existing.pb = pb
            existing.created_at = datetime.now()
        else:
            record = MarketIndex(
                symbol=symbol, index_name=index_name, trade_date=trade_date,
                open=open_, high=high, low=low, close=close,
                volume=volume, amount=amount, pe_ttm=pe_ttm, pb=pb
            )
            self.session.add(record)

    def get_index_data(self, symbol: str, start_date: date = None,
                       end_date: date = None) -> list:
        """Get index data for a symbol within date range."""
        q = self.session.query(MarketIndex).filter(MarketIndex.symbol == symbol)
        if start_date:
            q = q.filter(MarketIndex.trade_date >= start_date)
        if end_date:
            q = q.filter(MarketIndex.trade_date <= end_date)
        return q.order_by(MarketIndex.trade_date).all()

    def get_latest_index_date(self, symbol: str) -> Optional[date]:
        """Get the most recent trade date for an index."""
        result = self.session.query(func.max(MarketIndex.trade_date)).filter(
            MarketIndex.symbol == symbol
        ).scalar()
        return result

    # ================================================================
    # Fund Basic Info
    # ================================================================
    def upsert_fund_info(self, fund_code: str, fund_name: str, fund_type: str,
                         management_company: str = None, manager_name: str = None,
                         manager_start_date: date = None, inception_date: date = None,
                         aum_yuan: float = None, management_fee_pct: float = None,
                         custodian_fee_pct: float = None, benchmark_index: str = None,
                         investment_style: str = None, is_etf: bool = False,
                         risk_level: str = None):
        """Insert or update fund basic info."""
        existing = self.session.query(FundBasicInfo).filter(
            FundBasicInfo.fund_code == fund_code
        ).first()
        if existing:
            existing.fund_name = fund_name
            if fund_type:
                existing.fund_type = fund_type
            if management_company:
                existing.management_company = management_company
            if manager_name:
                existing.manager_name = manager_name
            if manager_start_date:
                existing.manager_start_date = manager_start_date
            if inception_date:
                existing.inception_date = inception_date
            if aum_yuan is not None:
                existing.aum_yuan = aum_yuan
            if management_fee_pct is not None:
                existing.management_fee_pct = management_fee_pct
            if custodian_fee_pct is not None:
                existing.custodian_fee_pct = custodian_fee_pct
            existing.updated_at = datetime.now()
        else:
            record = FundBasicInfo(
                fund_code=fund_code, fund_name=fund_name, fund_type=fund_type,
                management_company=management_company, manager_name=manager_name,
                manager_start_date=manager_start_date, inception_date=inception_date,
                aum_yuan=aum_yuan, management_fee_pct=management_fee_pct,
                custodian_fee_pct=custodian_fee_pct, benchmark_index=benchmark_index,
                investment_style=investment_style, is_etf=is_etf, risk_level=risk_level
            )
            self.session.add(record)

    def get_fund_info(self, fund_code: str) -> Optional[FundBasicInfo]:
        return self.session.query(FundBasicInfo).filter(
            FundBasicInfo.fund_code == fund_code
        ).first()

    def get_funds_by_type(self, fund_type: str, limit: int = None) -> list:
        q = self.session.query(FundBasicInfo).filter(
            FundBasicInfo.fund_type == fund_type
        )
        if limit:
            q = q.limit(limit)
        return q.all()

    def get_all_active_funds(self) -> list:
        return self.session.query(FundBasicInfo).filter(
            FundBasicInfo.can_buy == True
        ).all()

    # ================================================================
    # Fund NAV
    # ================================================================
    def upsert_fund_nav(self, fund_code: str, trade_date: date, nav: float,
                        accumulated_nav: float = None, daily_return: float = None,
                        subscription_status: str = None, redemption_status: str = None):
        """Insert or update fund NAV record."""
        existing = self.session.query(FundNav).filter(
            FundNav.fund_code == fund_code,
            FundNav.trade_date == trade_date
        ).first()
        if existing:
            existing.nav = nav
            if accumulated_nav is not None:
                existing.accumulated_nav = accumulated_nav
            if daily_return is not None:
                existing.daily_return = daily_return
            existing.created_at = datetime.now()
        else:
            record = FundNav(
                fund_code=fund_code, trade_date=trade_date, nav=nav,
                accumulated_nav=accumulated_nav, daily_return=daily_return,
                subscription_status=subscription_status,
                redemption_status=redemption_status
            )
            self.session.add(record)

    def get_fund_nav(self, fund_code: str, start_date: date = None,
                     end_date: date = None) -> list:
        q = self.session.query(FundNav).filter(FundNav.fund_code == fund_code)
        if start_date:
            q = q.filter(FundNav.trade_date >= start_date)
        if end_date:
            q = q.filter(FundNav.trade_date <= end_date)
        return q.order_by(FundNav.trade_date).all()

    def get_latest_fund_nav_date(self, fund_code: str) -> Optional[date]:
        result = self.session.query(func.max(FundNav.trade_date)).filter(
            FundNav.fund_code == fund_code
        ).scalar()
        return result

    # ================================================================
    # Fund Performance
    # ================================================================
    def upsert_fund_performance(self, fund_code: str, calc_date: date, **metrics):
        existing = self.session.query(FundPerformance).filter(
            FundPerformance.fund_code == fund_code,
            FundPerformance.calc_date == calc_date
        ).first()
        if existing:
            for key, value in metrics.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            existing.updated_at = datetime.now()
        else:
            record = FundPerformance(fund_code=fund_code, calc_date=calc_date, **metrics)
            self.session.add(record)

    def get_fund_performance(self, fund_code: str, calc_date: date = None) -> Optional[FundPerformance]:
        q = self.session.query(FundPerformance).filter(
            FundPerformance.fund_code == fund_code
        )
        if calc_date:
            q = q.filter(FundPerformance.calc_date == calc_date)
        return q.order_by(desc(FundPerformance.calc_date)).first()

    # ================================================================
    # Fund Score
    # ================================================================
    def upsert_fund_score(self, fund_code: str, calc_date: date, **scores):
        existing = self.session.query(FundScore).filter(
            FundScore.fund_code == fund_code,
            FundScore.calc_date == calc_date
        ).first()
        if existing:
            for key, value in scores.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            existing.updated_at = datetime.now()
        else:
            record = FundScore(fund_code=fund_code, calc_date=calc_date, **scores)
            self.session.add(record)

    def get_top_funds_by_score(self, fund_type: str = None, calc_date: date = None,
                               limit: int = 20) -> list:
        q = self.session.query(FundScore, FundBasicInfo).join(
            FundBasicInfo, FundScore.fund_code == FundBasicInfo.fund_code
        )
        if fund_type:
            q = q.filter(FundBasicInfo.fund_type == fund_type)
        if calc_date:
            q = q.filter(FundScore.calc_date == calc_date)
        return q.order_by(desc(FundScore.total_score)).limit(limit).all()

    # ================================================================
    # Portfolio
    # ================================================================
    def create_portfolio(self, name: str, initial_capital: float,
                         risk_profile: str, description: str = None) -> Portfolio:
        portfolio = Portfolio(
            name=name, initial_capital=initial_capital,
            risk_profile=risk_profile, created_at=date.today(),
            description=description
        )
        self.session.add(portfolio)
        self.session.flush()
        return portfolio

    def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        return self.session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    def get_all_portfolios(self, active_only: bool = False) -> list:
        q = self.session.query(Portfolio)
        if active_only:
            q = q.filter(Portfolio.is_active == True)
        return q.order_by(Portfolio.id).all()

    def get_portfolio_holdings(self, portfolio_id: int) -> list:
        return self.session.query(Holding).filter(
            Holding.portfolio_id == portfolio_id
        ).all()

    # ================================================================
    # Holdings
    # ================================================================
    def add_holding(self, portfolio_id: int, fund_code: str, shares: float,
                    avg_cost: float, purchase_date: date, notes: str = None):
        existing = self.session.query(Holding).filter(
            Holding.portfolio_id == portfolio_id,
            Holding.fund_code == fund_code
        ).first()
        if existing:
            # Weighted average cost
            total_value = existing.shares * existing.avg_cost + shares * avg_cost
            existing.shares += shares
            existing.avg_cost = total_value / existing.shares if existing.shares > 0 else 0
            existing.notes = notes or existing.notes
        else:
            record = Holding(
                portfolio_id=portfolio_id, fund_code=fund_code,
                shares=shares, avg_cost=avg_cost, purchase_date=purchase_date,
                notes=notes
            )
            self.session.add(record)

    def remove_holding(self, portfolio_id: int, fund_code: str, shares: float = None):
        holding = self.session.query(Holding).filter(
            Holding.portfolio_id == portfolio_id,
            Holding.fund_code == fund_code
        ).first()
        if holding:
            if shares is None or shares >= holding.shares:
                self.session.delete(holding)
            else:
                holding.shares -= shares

    def update_holding_nav(self, portfolio_id: int, fund_code: str,
                           nav: float, update_date: date):
        holding = self.session.query(Holding).filter(
            Holding.portfolio_id == portfolio_id,
            Holding.fund_code == fund_code
        ).first()
        if holding:
            holding.last_nav = nav
            holding.last_update_date = update_date

    # ================================================================
    # Transactions
    # ================================================================
    def add_transaction(self, portfolio_id: int, fund_code: str,
                        transaction_type: str, transaction_date: date,
                        shares: float, price: float, amount: float,
                        fee: float = 0, notes: str = None) -> Transaction:
        txn = Transaction(
            portfolio_id=portfolio_id, fund_code=fund_code,
            transaction_type=transaction_type, transaction_date=transaction_date,
            shares=shares, price=price, amount=amount, fee=fee, notes=notes
        )
        self.session.add(txn)
        return txn

    def get_transactions(self, portfolio_id: int = None,
                         fund_code: str = None, limit: int = 100) -> list:
        q = self.session.query(Transaction)
        if portfolio_id:
            q = q.filter(Transaction.portfolio_id == portfolio_id)
        if fund_code:
            q = q.filter(Transaction.fund_code == fund_code)
        return q.order_by(desc(Transaction.transaction_date)).limit(limit).all()

    # ================================================================
    # Alerts
    # ================================================================
    def add_alert(self, alert_type: str, severity: str, message: str,
                  portfolio_id: int = None, fund_code: str = None) -> Alert:
        alert = Alert(
            portfolio_id=portfolio_id, fund_code=fund_code,
            alert_type=alert_type, severity=severity, message=message
        )
        self.session.add(alert)
        return alert

    def get_alerts(self, portfolio_id: int = None, is_read: bool = None,
                   limit: int = 50) -> list:
        q = self.session.query(Alert)
        if portfolio_id:
            q = q.filter(Alert.portfolio_id == portfolio_id)
        if is_read is not None:
            q = q.filter(Alert.is_read == is_read)
        return q.order_by(desc(Alert.triggered_at)).limit(limit).all()

    def mark_alert_read(self, alert_id: int):
        alert = self.session.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.is_read = True

    # ================================================================
    # Sector Performance
    # ================================================================
    def upsert_sector_performance(self, sector_code: str, sector_name: str,
                                  trade_date: date, **metrics):
        existing = self.session.query(SectorPerformance).filter(
            SectorPerformance.sector_code == sector_code,
            SectorPerformance.trade_date == trade_date
        ).first()
        if existing:
            for key, value in metrics.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            existing.updated_at = datetime.now()
        else:
            record = SectorPerformance(
                sector_code=sector_code, sector_name=sector_name,
                trade_date=trade_date, **metrics
            )
            self.session.add(record)

    # ================================================================
    # Macro Indicators
    # ================================================================
    def upsert_macro_indicator(self, indicator_type: str, period: str,
                               value: float, yoy_change: float = None,
                               mom_change: float = None):
        existing = self.session.query(MacroIndicator).filter(
            MacroIndicator.indicator_type == indicator_type,
            MacroIndicator.period == period
        ).first()
        if existing:
            existing.value = value
            if yoy_change is not None:
                existing.yoy_change = yoy_change
            if mom_change is not None:
                existing.mom_change = mom_change
            existing.updated_at = datetime.now()
        else:
            record = MacroIndicator(
                indicator_type=indicator_type, period=period,
                value=value, yoy_change=yoy_change, mom_change=mom_change
            )
            self.session.add(record)

    def get_macro_indicator(self, indicator_type: str, periods: int = 12) -> list:
        return self.session.query(MacroIndicator).filter(
            MacroIndicator.indicator_type == indicator_type
        ).order_by(desc(MacroIndicator.period)).limit(periods).all()

    # ================================================================
    # Utility
    # ================================================================
    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def close(self):
        self.session.close()
