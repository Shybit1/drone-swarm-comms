"""
src/kmeans_deployment.py

K-Means Clustering for Initial Drone Deployment

Identifies fire hotspots and assigns drones to optimal positions
for maximum coverage and early fire suppression.
"""

import numpy as np
import math
from typing import List, Tuple
from constants import clamp
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# KMEANS CLUSTERING
# ============================================================================

class KMeansDeployment:
    """
    K-Means Clustering for Fire Hotspot Detection
    
    Algorithm:
    1. Given N suspected fire locations
    2. Run K-means with K = num_clusters
    3. Compute cluster centroids
    4. Assign leader drones to centroids
    5. Assign followers to nearest leader
    
    This optimizes spatial coverage for multi-zone fire response.
    """
    
    def __init__(self, n_clusters: int = 3, max_iterations: int = 100, seed: int = None):
        """
        Initialize K-means.
        
        Args:
            n_clusters: Number of clusters (deployment zones)
            max_iterations: Max iterations for convergence
            seed: RNG seed
        """
        self.n_clusters = n_clusters
        self.max_iterations = max_iterations
        self.rng = np.random.RandomState(seed)
        
        self.centroids = None
        self.labels = None
        self.converged = False
    
    def cluster(self, fire_points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Cluster fire points and return centroids.
        
        Args:
            fire_points: List of (x, y) coordinates
        
        Returns:
            List of centroid (x, y) coordinates
        """
        if not fire_points or len(fire_points) == 0:
            logger.warning("No fire points provided to K-means")
            return []
        
        points = np.array(fire_points, dtype=np.float32)
        n_points = len(points)
        
        # Limit clusters to number of points
        n_clusters = min(self.n_clusters, n_points)
        
        # Initialize centroids randomly from points
        indices = self.rng.choice(n_points, size=n_clusters, replace=False)
        self.centroids = points[indices].copy()
        
        # Iterative K-means
        for iteration in range(self.max_iterations):
            # Assign points to nearest centroid
            distances = np.linalg.norm(
                points[:, np.newaxis] - self.centroids,
                axis=2
            )
            self.labels = np.argmin(distances, axis=1)
            
            # Update centroids
            new_centroids = np.zeros_like(self.centroids)
            for k in range(n_clusters):
                cluster_points = points[self.labels == k]
                if len(cluster_points) > 0:
                    new_centroids[k] = cluster_points.mean(axis=0)
                else:
                    # Keep old centroid if cluster is empty
                    new_centroids[k] = self.centroids[k]
            
            # Check convergence
            if np.allclose(self.centroids, new_centroids, atol=0.1):
                self.converged = True
                logger.info(f"K-means converged in {iteration+1} iterations")
                break
            
            self.centroids = new_centroids
        
        if not self.converged:
            logger.warning(f"K-means did not converge after {self.max_iterations} iterations")
        
        # Convert back to list of tuples
        return [(float(c[0]), float(c[1])) for c in self.centroids]
    
    def get_centroids(self) -> List[Tuple[float, float]]:
        """Get current centroids."""
        if self.centroids is None:
            return []
        return [(float(c[0]), float(c[1])) for c in self.centroids]
    
    def assign_leaders(self, num_leaders: int) -> List[Tuple[float, float]]:
        """
        Get leader deployment positions (centroids).
        
        Args:
            num_leaders: Number of leaders available
        
        Returns:
            List of (x, y) positions for leaders
        """
        centroids = self.get_centroids()
        
        # Use first num_leaders centroids
        leader_positions = centroids[:min(num_leaders, len(centroids))]
        
        # Pad with None if fewer centroids than leaders
        while len(leader_positions) < num_leaders:
            leader_positions.append(None)
        
        return leader_positions
    
    def assign_followers_to_leader(self, follower_count: int,
                                  leader_positions: List[Tuple[float, float]]) -> dict:
        """
        Assign followers to nearest leader.
        
        Args:
            follower_count: Number of followers available
            leader_positions: List of leader (x, y) positions
        
        Returns:
            Dictionary mapping follower_id -> leader_id
        """
        assignments = {}
        
        # Distribute followers roughly evenly among leaders
        followers_per_leader = max(1, follower_count // len(leader_positions))
        
        follower_id = 0
        for leader_id, leader_pos in enumerate(leader_positions):
            if leader_pos is None:
                continue
            
            for _ in range(followers_per_leader):
                if follower_id >= follower_count:
                    break
                assignments[follower_id] = leader_id
                follower_id += 1
        
        # Assign remaining followers to random leaders
        while follower_id < follower_count:
            leader_id = self.rng.randint(0, len(leader_positions))
            assignments[follower_id] = leader_id
            follower_id += 1
        
        return assignments
