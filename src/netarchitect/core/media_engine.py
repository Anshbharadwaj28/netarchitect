from .exceptions import PhysicalDistanceViolationError
from .models import PhysicalLinkRequest, PhysicalLinkRecommendation


class MediaEngine:
    @staticmethod
    def evaluate_link(link: PhysicalLinkRequest) -> PhysicalLinkRecommendation:
        dist = link.distance_meters
        override = link.medium_override.upper() if link.medium_override else None

        if override in ["CAT6", "CAT6A", "COPPER", "10GBASE-T"]:
            if dist > 100.0:
                raise PhysicalDistanceViolationError(
                    f"Physical media violation: Link '{link.source}' -> '{link.destination}' requests copper "
                    f"over {dist:.1f}m. IEEE 802.3an 10GBASE-T enforces a hard 100m physical boundary due to "
                    f"insertion loss, high-frequency attenuation, and near-end crosstalk (NEXT)."
                )

        if dist <= 100.0:
            return PhysicalLinkRecommendation(
                source=link.source,
                destination=link.destination,
                distance_meters=dist,
                recommended_media="Cat6a U/FTP or F/UTP",
                standard="IEEE 802.3an (10GBASE-T)",
                transceiver_type="RJ-45 Native / SFP-10G-T-S",
                wavelength_nm=None,
                engineering_justification=(
                    f"Link distance of {dist:.1f}m is within the 100-meter electrical channel limit specified "
                    "by IEEE 802.3an. 10GBASE-T over Cat6a delivers 10 Gbps throughput at 500 MHz bandwidth "
                    "with superior power efficiency and eliminates costly optical transceivers for intra-building runs."
                )
            )
        elif 100.0 < dist <= 400.0:
            return PhysicalLinkRecommendation(
                source=link.source,
                destination=link.destination,
                distance_meters=dist,
                recommended_media="OM4 Multi-Mode Fiber (MMF 50/125µm)",
                standard="IEEE 802.3ae (10GBASE-SR)",
                transceiver_type="SFP-10G-SR",
                wavelength_nm=850,
                engineering_justification=(
                    f"Link distance of {dist:.1f}m exceeds the 100m copper limit but sits safely within the 400m "
                    "operating range of OM4 laser-optimized MMF. OM4 provides an effective modal bandwidth of "
                    "4700 MHz·km at 850nm VCSEL transmission, avoiding chromatic dispersion while lowering optics cost."
                )
            )
        else:
            transceiver = "SFP-10G-LR (1310nm, up to 10km)" if dist <= 10000.0 else "SFP-10G-ER (1550nm, up to 40km)"
            wavelength = 1310 if dist <= 10000.0 else 1550
            return PhysicalLinkRecommendation(
                source=link.source,
                destination=link.destination,
                distance_meters=dist,
                recommended_media="OS2 Single-Mode Fiber (SMF 9/125µm)",
                standard="IEEE 802.3ae (10GBASE-LR/ER)",
                transceiver_type=transceiver,
                wavelength_nm=wavelength,
                engineering_justification=(
                    f"Link distance of {dist:.1f}m exceeds the 400m dispersion envelope of multimode fiber. "
                    "OS2 single-mode fiber with a 9µm core eliminates intermodal dispersion entirely, "
                    f"providing an optical attenuation budget <= 0.4 dB/km at {wavelength}nm for metropolitan/WAN spans."
                )
            )