"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        ##### Begin Stage 10A #####
        self.history = {}
        ##### End Stage 10A #####

    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        ##### Begin Stage 1 #####
        latency = self.ports.get_latency(port)
        entry = TableEntry(dst = host, port = port, latency = latency, expire_time=FOREVER)
        self.table[host] = entry
        ##### End Stage 1 #####

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        
        ##### Begin Stage 2 #####
        dst = packet.dst
        entry = self.table.get(dst)
        if entry is None or entry.latency >= INFINITY:
            return
        self.send(packet, port = entry.port)
        ##### End Stage 2 #####

    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        
        ##### Begin Stages 3, 6, 7, 8, 10 #####
        if single_port is not None:
            ports = [single_port]
        else:
            ports = self.ports.get_all_ports()
        for port in ports:
            if port not in self.history:
                self.history[port] = {}
            for dst, entry in self.table.items():
                if self.SPLIT_HORIZON and port == entry.port:
                    continue
                elif self.POISON_REVERSE and port == entry.port:
                    advertised_latency = INFINITY
                else:
                    advertised_latency = min(entry.latency, INFINITY)
                send_update = False
                if force:
                    send_update = True
                else:
                    last_advertised_latency = self.history[port].get(dst)
                    if last_advertised_latency != advertised_latency:
                        send_update = True
                if send_update:
                    self.send_route(port, dst, advertised_latency)
                    self.history[port][dst] = advertised_latency
        ##### End Stages 3, 6, 7, 8, 10 #####

    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        
        ##### Begin Stages 5, 9 #####
        current_time = api.current_time()
        expired_destinations = []
        for dst, entry in self.table.items():
            if entry.expire_time <= current_time:
                expired_destinations.append((dst, entry))
        for dst, entry in expired_destinations:
            if self.POISON_EXPIRED:
                poisoned_entry = TableEntry(dst=dst, port = entry.port, latency=INFINITY, expire_time=current_time+self.ROUTE_TTL)
                self.table[dst] = poisoned_entry
            else:
                self.table.pop(dst)
        ##### End Stages 5, 9 #####

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        
        ##### Begin Stages 4, 10 #####
        neighbor_cost = self.ports.get_latency(port)
        total_cost = neighbor_cost + route_latency  

        table_updated = False  
        expire_time = api.current_time() + self.ROUTE_TTL
        if route_dst in self.table:
            entry = self.table[route_dst]
            if port == entry.port:
                new_entry = TableEntry(dst=route_dst, port=port, latency=total_cost, expire_time=expire_time)
                if new_entry != entry:
                    self.table[route_dst] = new_entry
                    table_updated = True
                else:
                    self.table[route_dst] = TableEntry(dst=entry.dst, port=entry.port, latency=entry.latency, expire_time=expire_time)
            elif total_cost < entry.latency:
                new_entry = TableEntry(dst=route_dst, port=port, latency=total_cost, expire_time=expire_time)
                self.table[route_dst] = new_entry
                table_updated = True
            else:
                pass
        else:
            new_entry = TableEntry(dst=route_dst, port=port, latency=total_cost, expire_time=expire_time)
            self.table[route_dst] = new_entry
            table_updated = True

        if table_updated:
            self.send_routes(force=False)
    
        ##### End Stages 4, 10 #####

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        ##### Begin Stage 10B #####
        if self.SEND_ON_LINK_UP:
            if port not in self.history:
                self.history[port] = {}
            self.send_routes(force=True, single_port=port)
        ##### End Stage 10B #####

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router goes down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)

        ##### Begin Stage 10B #####
        if port in self.history:
            self.history.pop(port, None)
        routes_updated = False
        for dst, entry in list(self.table.items()):
            if entry.port == port:
                if self.POISON_ON_LINK_DOWN:
                    poisoned_entry = TableEntry(dst=dst, port=entry.port, latency=INFINITY, expire_time=api.current_time() + self.ROUTE_TTL)
                    self.table[dst] = poisoned_entry
                    routes_updated = True
                else:
                    self.table.pop(dst)
                    routes_updated = True
        if routes_updated:
            self.send_routes(force=False)
        ##### End Stage 10B #####

    # Feel free to add any helper methods!
