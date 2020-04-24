# PyCO2SYS: marine carbonate system calculations in Python.
# Copyright (C) 2020  Matthew Paul Humphreys et al.  (GNU GPLv3)
"""Calculate saturation states of soluble solids."""
from autograd.numpy import exp, log10, sqrt, where
from . import convert
from .constants import RGasConstant


def _deltaKappaCalcite_I75(TempC):
    """Delta and kappa terms for calcite solubility [I75]."""
    # Note that Millero, GCA 1995 has typos:
    #   (-.5304, -.3692, and 10^3 for Kappa factor)
    deltaVKCa = -48.76 + 0.5304 * TempC
    KappaKCa = (-11.76 + 0.3692 * TempC) / 1000
    return deltaVKCa, KappaKCa


def k_calcite_M83(TempK, Sal, Pbar):
    """Calcite solubility following M83."""
    logKCa = -171.9065 - 0.077993 * TempK + 2839.319 / TempK
    logKCa = logKCa + 71.595 * log10(TempK)
    logKCa = logKCa + (-0.77712 + 0.0028426 * TempK + 178.34 / TempK) * sqrt(Sal)
    logKCa = logKCa - 0.07711 * Sal + 0.0041249 * sqrt(Sal) * Sal
    # sd fit = .01 (for Sal part, not part independent of Sal)
    KCa = 10.0 ** logKCa  # this is in (mol/kg-SW)^2 at zero pressure
    # Add pressure correction for calcite [I75, M79]
    TempC = convert.TempK2C(TempK)
    deltaVKCa, KappaKCa = _deltaKappaCalcite_I75(TempC)
    lnKCafac = (-deltaVKCa + 0.5 * KappaKCa * Pbar) * Pbar / (RGasConstant * TempK)
    KCa = KCa * exp(lnKCafac)
    return KCa


def k_aragonite_M83(TempK, Sal, Pbar):
    """Aragonite solubility following M83 with pressure correction of I75."""
    logKAr = -171.945 - 0.077993 * TempK + 2903.293 / TempK
    logKAr = logKAr + 71.595 * log10(TempK)
    logKAr = logKAr + (-0.068393 + 0.0017276 * TempK + 88.135 / TempK) * sqrt(Sal)
    logKAr = logKAr - 0.10018 * Sal + 0.0059415 * sqrt(Sal) * Sal
    # sd fit = .009 (for Sal part, not part independent of Sal)
    KAr = 10.0 ** logKAr  # this is in (mol/kg-SW)^2
    # Add pressure correction for aragonite [M79]:
    TempC = convert.TempK2C(TempK)
    deltaVKCa, KappaKCa = _deltaKappaCalcite_I75(TempC)
    # Same as Millero, GCA 1995 except for typos (-.5304, -.3692,
    #   and 10^3 for Kappa factor)
    deltaVKAr = deltaVKCa + 2.8
    KappaKAr = KappaKCa
    lnKArfac = (-deltaVKAr + 0.5 * KappaKAr * Pbar) * Pbar / (RGasConstant * TempK)
    KAr = KAr * exp(lnKArfac)
    return KAr


def k_calcite_I75(TempK, Sal, Pbar):
    """Calcite solubility following ICHP73 with no pressure correction.
    For use with GEOSECS constants.
    """
    # === CO2SYS.m comments: =======
    # *** CalculateKCaforGEOSECS:
    # Ingle et al, Marine Chemistry 1:295-307, 1973 is referenced in
    # (quoted in Takahashi et al, GEOSECS Pacific Expedition v. 3, 1982
    # but the fit is actually from Ingle, Marine Chemistry 3:301-319, 1975).
    # This is in (mol/kg-SW)^2
    KCa = 0.0000001 * (
        -34.452
        - 39.866 * Sal ** (1 / 3)
        + 110.21 * log10(Sal)
        - 0.0000075752 * TempK ** 2
    )
    # Now add pressure correction
    # === CO2SYS.m comments: =======
    # Culberson and Pytkowicz, Limnology and Oceanography 13:403-417, 1968
    # (quoted in Takahashi et al, GEOSECS Pacific Expedition v. 3, 1982
    # but their paper is not even on this topic).
    # The fits appears to be new in the GEOSECS report.
    # I can't find them anywhere else.
    TempC = convert.TempK2C(TempK)
    KCa = KCa * exp((36 - 0.2 * TempC) * Pbar / (RGasConstant * TempK))
    return KCa


def k_aragonite_GEOSECS(TempK, Sal, Pbar):
    """Aragonite solubility following ICHP73 with no pressure correction.
    For use with GEOSECS constants.
    """
    # === CO2SYS.m comments: =======
    # *** CalculateKArforGEOSECS:
    # Berner, R. A., American Journal of Science 276:713-730, 1976:
    # (quoted in Takahashi et al, GEOSECS Pacific Expedition v. 3, 1982)
    KCa = k_calcite_I75(TempK, Sal, Pbar)
    KAr = 1.45 * KCa  # this is in (mol/kg-SW)^2
    # Berner (p. 722) states that he uses 1.48.
    # It appears that 1.45 was used in the GEOSECS calculations
    # Now add pressure correction
    # === CO2SYS.m comments: =======
    # Culberson and Pytkowicz, Limnology and Oceanography 13:403-417, 1968
    # (quoted in Takahashi et al, GEOSECS Pacific Expedition v. 3, 1982
    # but their paper is not even on this topic).
    # The fits appears to be new in the GEOSECS report.
    # I can't find them anywhere else.
    TempC = convert.TempK2C(TempK)
    KAr = KAr * exp((33.3 - 0.22 * TempC) * Pbar / (RGasConstant * TempK))
    return KAr


def calcite(Sal, TempK, Pbar, CARB, TCa, WhichKs, K1, K2):
    """Calculate calcite solubility.

    This calculates omega, the solubility ratio, for calcite.
    This is defined by: Omega = [CO3--]*[Ca++]/Ksp,
          where Ksp is the solubility product (KCa).

    Based on CaSolubility, version 01.05, 05-23-97, written by Ernie Lewis.
    """
    # Get stoichiometric solubility constant
    F = (WhichKs == 6) | (WhichKs == 7)  # GEOSECS values
    KCa = where(F, k_calcite_I75(TempK, Sal, Pbar), k_calcite_M83(TempK, Sal, Pbar))
    # Calculate saturation state
    OmegaCa = CARB * TCa / KCa
    return OmegaCa


def aragonite(Sal, TempK, Pbar, CARB, TCa, WhichKs, K1, K2):
    """Calculate aragonite solubility.

    This calculates omega, the solubility ratio, for aragonite.
    This is defined by: Omega = [CO3--]*[Ca++]/Ksp,
          where Ksp is the solubility product (KAr).

    Based on CaSolubility, version 01.05, 05-23-97, written by Ernie Lewis.
    """
    # Get stoichiometric solubility constant
    F = (WhichKs == 6) | (WhichKs == 7)  # GEOSECS values
    KAr = where(
        F, k_aragonite_GEOSECS(TempK, Sal, Pbar), k_aragonite_M83(TempK, Sal, Pbar)
    )
    # Calculate saturation state
    OmegaAr = CARB * TCa / KAr
    return OmegaAr


def CaCO3(Sal, TempC, Pdbar, CARB, TCa, WhichKs, K1, K2):
    """Calculate calcite and aragonite solubility.

    This calculates omega, the solubility ratio, for calcite and aragonite.
    This is defined by: Omega = [CO3--]*[Ca++]/Ksp,
          where Ksp is the solubility product (either KCa or KAr).
    These are from: M83, I75, M79, ICHP73, B76, TWB82 and CP68.

    Based on CaSolubility, version 01.05, 05-23-97, written by Ernie Lewis.
    """
    # Convert units
    TempK = convert.TempC2K(TempC)
    Pbar = convert.Pdbar2bar(Pdbar)
    # Calculate saturation states
    OmegaCa = calcite(Sal, TempK, Pbar, CARB, TCa, WhichKs, K1, K2)
    OmegaAr = aragonite(Sal, TempK, Pbar, CARB, TCa, WhichKs, K1, K2)
    return OmegaCa, OmegaAr
