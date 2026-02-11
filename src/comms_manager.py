"""
src/comms_manager.py

Communication Layer for Drone Swarm

Implements dual-mode networking:
- MQLink: High-bandwidth cellular (MQTT broker)
- UAVConnector: Ad-hoc RF (UDP broadcast with range gating)

All messages use Protocol Buffers for serialization (no JSON/XML).
Communication is gated by DETM (only transmit on trigger).
"""

import asyncio
import socket
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from constants import (
    MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_QOS,
    AD_HOC_BROADCAST_RANGE_M
)

logger = logging.getLogger(__name__)

# ============================================================================
# COMMUNICATION MODES
# ============================================================================

@dataclass
class MessageMetadata:
    """Metadata for transmitted message."""
    sender_id: int
    receiver_id: int  # 0 = broadcast
    timestamp_us: int
    message_type: str  # "telemetry", "command", "neighbor_estimate"
    payload_size_bytes: int
    rssi_dbm: Optional[float] = None
    latency_ms: Optional[float] = None


# ============================================================================
# MQTT COMMUNICATION (MQLINK MODE)
# ============================================================================

class MQLinkCommunicator:
    """
    MQLink Mode: High-Bandwidth Cellular Emulation
    
    Uses MQTT broker for drone-to-cloud and drone-to-drone messaging.
    Provides:
    - Reliable delivery (QoS 1)
    - Global reach (all drones can reach all drones)
    - Moderate latency (5-50ms simulated)
    - High bandwidth
    
    Topic structure:
    - swarm/drone{i}/telemetry: Drone i publishes state
    - swarm/drone{i}/command: Commands to drone i
    - swarm/broadcast: Broadcast messages
    
    Note: In this simulation, we mock MQTT locally to avoid external dependencies.
    In production, would use real MQTT broker (Mosquitto, HiveMQ, etc.)
    """
    
    def __init__(self, broker_host: str = MQTT_BROKER_HOST,
                 broker_port: int = MQTT_BROKER_PORT):
        """
        Initialize MQTT communicator.
        
        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        
        # Message store (simulates broker)
        self.message_store: Dict[str, List[dict]] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        
        logger.info(f"MQLink initialized: {broker_host}:{broker_port}")
    
    def publish(self, topic: str, message: bytes, qos: int = MQTT_QOS) -> bool:
        """
        Publish message to topic.
        
        Args:
            topic: MQTT topic (e.g., "swarm/drone1/telemetry")
            message: Message payload (bytes)
            qos: Quality of service (0, 1, or 2)
        
        Returns:
            True if published successfully
        """
        if topic not in self.message_store:
            self.message_store[topic] = []
        
        self.message_store[topic].append(message)
        
        # Notify subscribers
        if topic in self.subscribers:
            for callback in self.subscribers[topic]:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Subscriber error: {e}")
        
        logger.debug(f"MQTT published to {topic}: {len(message)} bytes")
        return True
    
    def subscribe(self, topic: str, callback: Callable) -> None:
        """
        Subscribe to topic.
        
        Args:
            topic: MQTT topic
            callback: Function to call when message received
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        
        self.subscribers[topic].append(callback)
        logger.debug(f"MQTT subscribed to {topic}")
    
    def get_messages(self, topic: str) -> List[bytes]:
        """Get all messages on topic."""
        return self.message_store.get(topic, [])
    
    def clear_messages(self, topic: str) -> None:
        """Clear message buffer for topic."""
        if topic in self.message_store:
            self.message_store[topic].clear()


# ============================================================================
# UDP COMMUNICATION (UAVCONNECTOR MODE)
# ============================================================================

class UAVConnectorBroadcaster:
    """
    UAVConnector Mode: Ad-Hoc RF Communication
    
    Uses UDP broadcast for local drone-to-drone links.
    Range-gated by virtual distance (simulating RF range limits).
    
    Features:
    - Leader ↔ Follower only (followers don't talk to each other)
    - Subject to RF degradation (packet loss, latency)
    - Physical range limits
    - Lossy delivery (no retransmission)
    
    Attributes:
        broadcast_range_m: Maximum transmission range
        drone_positions: Current positions (for range calculation)
        physics_engine: Reference to physics engine (for channel states)
    """
    
    def __init__(self, broadcast_range_m: float = AD_HOC_BROADCAST_RANGE_M,
                 physics_engine = None):
        """
        Initialize UAVConnector.
        
        Args:
            broadcast_range_m: RF range (meters)
            physics_engine: Physics engine for channel modeling
        """
        self.broadcast_range_m = broadcast_range_m
        self.physics_engine = physics_engine
        
        # Message queues per drone (simulates lossy RF medium)
        self.rx_queues: Dict[int, List[dict]] = {}
        
        logger.info(f"UAVConnector initialized: range={broadcast_range_m}m")
    
    def register_drone(self, drone_id: int) -> None:
        """Register drone for UAVConnector."""
        if drone_id not in self.rx_queues:
            self.rx_queues[drone_id] = []
    
    def broadcast(self, sender_id: int, message: bytes,
                 metadata: MessageMetadata) -> int:
        """
        Broadcast message from drone to all neighbors within range.
        
        Message delivery depends on:
        - Distance between drones
        - RF channel state (RSSI, packet loss)
        
        Args:
            sender_id: Sending drone ID
            message: Message payload
            metadata: Message metadata
        
        Returns:
            Number of successful deliveries
        """
        if self.physics_engine is None:
            logger.warning("PhysicsEngine not set, skipping broadcast")
            return 0
        
        delivered = 0
        
        # Iterate through all drones
        for receiver_id in self.rx_queues.keys():
            if receiver_id == sender_id:
                continue
            
            # Check distance
            distance = self.physics_engine.get_distance_between_drones(
                sender_id, receiver_id
            )
            
            if distance is None or distance > self.broadcast_range_m:
                continue  # Out of range
            
            # Check channel state for packet loss
            channel_state = self.physics_engine.get_channel_state(sender_id, receiver_id)
            if channel_state is None:
                continue
            
            # Probabilistic delivery based on packet loss
            import random
            if random.random() < channel_state.packet_loss_probability:
                logger.debug(
                    f"UAVConnector: packet loss {sender_id} → {receiver_id} "
                    f"(loss_prob={channel_state.packet_loss_probability:.2f})"
                )
                continue  # Packet lost
            
            # Deliver message
            rx_msg = {
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "message": message,
                "metadata": metadata,
                "rssi_dbm": channel_state.rssi_dbm,
                "latency_ms": channel_state.estimated_latency_ms,
            }
            
            self.rx_queues[receiver_id].append(rx_msg)
            delivered += 1
            
            logger.debug(
                f"UAVConnector: delivered {sender_id} → {receiver_id} "
                f"({len(message)} bytes, RSSI={channel_state.rssi_dbm:.1f}dBm)"
            )
        
        return delivered
    
    def receive(self, receiver_id: int) -> Optional[dict]:
        """
        Receive next message for drone.
        
        Args:
            receiver_id: Receiving drone ID
        
        Returns:
            Message dictionary or None if no messages
        """
        if receiver_id not in self.rx_queues:
            return None
        
        if len(self.rx_queues[receiver_id]) > 0:
            return self.rx_queues[receiver_id].pop(0)
        
        return None
    
    def clear_rx_queue(self, receiver_id: int) -> None:
        """Clear receive queue for drone."""
        if receiver_id in self.rx_queues:
            self.rx_queues[receiver_id].clear()


# ============================================================================
# UNIFIED COMMUNICATIONS MANAGER
# ============================================================================

class CommunicationsManager:
    """
    Unified Communications Manager
    
    Orchestrates both MQLink and UAVConnector modes.
    - Handles telemetry serialization/deserialization
    - Routes messages to appropriate mode
    - Tracks communication metrics
    
    Attributes:
        mqlink: MQTT communicator
        uav_connector: UDP broadcaster
        detm_controller: Reference to DETM for transmission gating
    """
    
    def __init__(self, detm_controller = None,
                 physics_engine = None):
        """
        Initialize communications manager.
        
        Args:
            detm_controller: DETM controller for transmission gating
            physics_engine: Physics engine for channel modeling
        """
        self.mqlink = MQLinkCommunicator()
        self.uav_connector = UAVConnectorBroadcaster(
            physics_engine=physics_engine
        )
        self.detm_controller = detm_controller
        self.physics_engine = physics_engine
        
        # Metrics
        self.messages_sent: Dict[int, int] = {}
        self.messages_received: Dict[int, int] = {}
        self.total_bytes_sent = 0
        self.total_bytes_received = 0
        
        logger.info("CommunicationsManager initialized")
    
    def register_drone(self, drone_id: int) -> None:
        """Register drone for communication."""
        self.uav_connector.register_drone(drone_id)
        self.messages_sent[drone_id] = 0
        self.messages_received[drone_id] = 0
    
    def publish_telemetry(self, drone_id: int, telemetry: dict,
                         serialized_bytes: bytes,
                         use_mode: str = "both") -> dict:
        """
        Publish drone telemetry.
        
        Can use MQLink, UAVConnector, or both.
        
        Args:
            drone_id: Sending drone ID
            telemetry: Telemetry dictionary (for metadata)
            serialized_bytes: Protobuf-serialized bytes
            use_mode: "mqlink", "uav", or "both"
        
        Returns:
            Dictionary with delivery stats
        """
        metadata = MessageMetadata(
            sender_id=drone_id,
            receiver_id=0,  # Broadcast
            timestamp_us=telemetry.get("timestamp_us", 0),
            message_type="telemetry",
            payload_size_bytes=len(serialized_bytes),
        )
        
        stats = {"mqlink": 0, "uav": 0}
        
        # MQLink publish
        if use_mode in ["mqlink", "both"]:
            topic = f"swarm/drone{drone_id}/telemetry"
            if self.mqlink.publish(topic, serialized_bytes):
                stats["mqlink"] = 1
                self.messages_sent[drone_id] += 1
                self.total_bytes_sent += len(serialized_bytes)
        
        # UAVConnector broadcast
        if use_mode in ["uav", "both"]:
            delivered = self.uav_connector.broadcast(
                drone_id, serialized_bytes, metadata
            )
            stats["uav"] = delivered
            self.messages_sent[drone_id] += 1
            self.total_bytes_sent += len(serialized_bytes)
        
        return stats
    
    def receive_messages(self, drone_id: int, mode: str = "uav") -> List[dict]:
        """
        Receive messages for drone.
        
        Args:
            drone_id: Receiving drone ID
            mode: "uav", "mqlink", or "both"
        
        Returns:
            List of received messages
        """
        messages = []
        
        if mode in ["uav", "both"]:
            while True:
                msg = self.uav_connector.receive(drone_id)
                if msg is None:
                    break
                messages.append(msg)
                self.messages_received[drone_id] += 1
                self.total_bytes_received += len(msg["message"])
        
        if mode in ["mqlink", "both"]:
            # Get from MQTT topics
            for topic in self.mqlink.message_store.keys():
                # Parse topic to see if it's for this drone
                if f"drone{drone_id}" in topic:
                    msgs = self.mqlink.get_messages(topic)
                    messages.extend([{"message": m} for m in msgs])
        
        return messages
    
    def get_metrics(self, drone_id: int) -> dict:
        """Get communication metrics for drone."""
        return {
            "drone_id": drone_id,
            "messages_sent": self.messages_sent.get(drone_id, 0),
            "messages_received": self.messages_received.get(drone_id, 0),
            "total_bytes_sent": self.total_bytes_sent,
            "total_bytes_received": self.total_bytes_received,
        }
    
    def get_global_metrics(self) -> dict:
        """Get global communication metrics."""
        total_sent = sum(self.messages_sent.values())
        total_received = sum(self.messages_received.values())
        
        return {
            "total_messages_sent": total_sent,
            "total_messages_received": total_received,
            "total_bytes_sent": self.total_bytes_sent,
            "total_bytes_received": self.total_bytes_received,
            "network_utilization_percent": (
                (self.total_bytes_sent + self.total_bytes_received) / 1e6 * 100
                if (self.total_bytes_sent + self.total_bytes_received) > 0
                else 0
            ),
        }
