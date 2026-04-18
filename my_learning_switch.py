from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()


class LearningSwitch(object):
    def __init__(self, connection):
        self.connection = connection
        self.mac_to_port = {}

        connection.addListeners(self)

    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            return

        in_port = event.port
        src = packet.src
        dst = packet.dst

        # Learn MAC address
        self.mac_to_port[src] = in_port
        log.info("Learned %s on port %s", src, in_port)

        # Firewall: Block h1 -> h3
        if str(src) == "00:00:00:00:00:01" and str(dst) == "00:00:00:00:00:03":
            log.warning("Blocked %s -> %s", src, dst)
            return

        # Forwarding logic
        if dst in self.mac_to_port:
            out_port = self.mac_to_port[dst]
            log.info("Forwarding %s -> %s via port %s", src, dst, out_port)
        else:
            out_port = of.OFPP_FLOOD
            log.info("Flooding %s -> %s", src, dst)

        # Install flow rule
        flow_mod = of.ofp_flow_mod()
        flow_mod.match.dl_dst = dst
        flow_mod.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(flow_mod)

        # Send current packet
        packet_out = of.ofp_packet_out()
        packet_out.data = event.ofp
        packet_out.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(packet_out)


class LearningSwitchController(object):
    def __init__(self):
        core.openflow.addListeners(self)

    def _handle_ConnectionUp(self, event):
        log.info("Switch connected: %s", event.connection)
        LearningSwitch(event.connection)


def launch():
    log.info("Custom Learning Switch with Firewall Running...")
    LearningSwitchController()