# RYZE Score Algorithms for Ranking Developers, Showcases, and Videos

import math
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func


class RyzeScoring:
    """
    Different algorithms to calculate RYZE scores that help the best content rise to the top
    """

    @staticmethod
    def bayesian_average(
        average_rating: float,
        total_ratings: int,
        confidence_threshold: int = 10,
        global_average: float = 3.0,
    ) -> float:
        """
        Bayesian Average - Most robust for small sample sizes

        Formula: ((confidence_threshold * global_average) + (total_ratings * average_rating)) /
                 (confidence_threshold + total_ratings)

        - confidence_threshold: Number of ratings needed for full confidence (default 10)
        - global_average: Platform average rating (default 3.0)

        Examples:
        - 5.0 stars, 1 rating = ~3.6 RYZE score
        - 5.0 stars, 10 ratings = ~4.7 RYZE score
        - 5.0 stars, 100 ratings = ~5.0 RYZE score
        """
        if total_ratings == 0:
            return 0

        return (
            (confidence_threshold * global_average) + (total_ratings * average_rating)
        ) / (confidence_threshold + total_ratings)

    @staticmethod
    def wilson_confidence_interval(
        positive_ratings: int, total_ratings: int, confidence: float = 0.95
    ) -> float:
        """
        Wilson Score Interval - Used by Reddit, most mathematically sound

        This gives a lower bound of the confidence interval for the true rating
        More conservative but very reliable

        Examples:
        - 5 positive out of 5 ratings = ~0.57 RYZE score
        - 50 positive out of 50 ratings = ~0.93 RYZE score
        - 500 positive out of 500 ratings = ~0.99 RYZE score
        """
        if total_ratings == 0:
            return 0

        # Convert 5-star ratings to positive/negative
        # Assume 4-5 stars = positive, 1-3 stars = negative for this calculation
        z = 1.96  # 95% confidence
        p = positive_ratings / total_ratings

        numerator = (
            p
            + (z * z) / (2 * total_ratings)
            - z
            * math.sqrt((p * (1 - p) + (z * z) / (4 * total_ratings)) / total_ratings)
        )
        denominator = 1 + (z * z) / total_ratings

        return numerator / denominator

    @staticmethod
    def weighted_rating(
        average_rating: float,
        total_ratings: int,
        rating_weight: float = 0.7,
        volume_weight: float = 0.3,
    ) -> float:
        """
        Simple Weighted Rating - Easy to understand and explain

        Formula: (rating_weight * normalized_rating) + (volume_weight * normalized_volume)

        - Normalizes rating to 0-1 scale (divide by 5)
        - Normalizes volume using logarithmic scale
        - Combines both with weights

        Examples:
        - 5.0 stars, 1 rating = ~0.72 RYZE score
        - 5.0 stars, 10 ratings = ~0.89 RYZE score
        - 5.0 stars, 100 ratings = ~1.0 RYZE score
        """
        if total_ratings == 0:
            return 0

        # Normalize rating (0-5 scale to 0-1 scale)
        normalized_rating = average_rating / 5.0

        # Normalize volume using log scale (prevents overwhelming by volume)
        # Using log10, so 1 rating = 0, 10 ratings = 1, 100 ratings = 2, etc.
        max_log_volume = 3  # Assuming 1000 ratings is "maximum"
        normalized_volume = min(math.log10(total_ratings + 1) / max_log_volume, 1.0)

        return (rating_weight * normalized_rating) + (volume_weight * normalized_volume)

    @staticmethod
    def imdb_formula(
        average_rating: float, total_ratings: int, minimum_votes: int = 25
    ) -> float:
        """
        IMDB's Top 250 Formula - Industry standard for movie rankings

        Formula: (v / (v + m)) * R + (m / (v + m)) * C
        Where:
        - v = number of votes/ratings
        - m = minimum votes required (default 25)
        - R = average rating
        - C = mean rating across the platform (assume 3.0)

        Examples:
        - 5.0 stars, 1 rating = ~3.08 RYZE score
        - 5.0 stars, 25 ratings = ~4.0 RYZE score
        - 5.0 stars, 100 ratings = ~4.8 RYZE score
        """
        platform_average = 3.0  # You can calculate this from your actual data

        return (total_ratings / (total_ratings + minimum_votes)) * average_rating + (
            minimum_votes / (total_ratings + minimum_votes)
        ) * platform_average

    @staticmethod
    def calculate_success_rate(average_rating: float, total_ratings: int) -> float:
        """
        Calculate success rate (RYZE score) as a percentage
        Higher ratings with more votes = higher success rate
        """
        ryze_score = RyzeScoring.bayesian_average(average_rating, total_ratings)
        # Convert to percentage (0-100 scale)
        return min(ryze_score * 20, 100)  # Multiply by 20 to convert 0-5 scale to 0-100

    @staticmethod
    def update_developer_ryze_score(db: Session, developer_profile_id: int):
        """Update a developer's RYZE score based on their ratings"""
        from ..models import (
            DeveloperProfile,
            DeveloperRating,
        )  # Import here to avoid circular imports

        # Get rating statistics
        stats = (
            db.query(
                func.avg(DeveloperRating.stars).label("average"),
                func.count(DeveloperRating.id).label("total"),
            )
            .filter(DeveloperRating.developer_id == developer_profile_id)
            .first()
        )

        average_rating = float(stats.average) if stats.average else 0.0
        total_ratings = stats.total

        # Calculate RYZE score
        ryze_score = RyzeScoring.bayesian_average(average_rating, total_ratings)
        success_rate = RyzeScoring.calculate_success_rate(average_rating, total_ratings)

        # Update the developer profile
        developer = (
            db.query(DeveloperProfile)
            .filter(DeveloperProfile.id == developer_profile_id)
            .first()
        )
        if developer:
            developer.rating = ryze_score
            developer.success_rate = success_rate
            db.commit()

        return {
            "average_rating": average_rating,
            "total_ratings": total_ratings,
            "ryze_score": ryze_score,
            "success_rate": success_rate,
        }


# Usage examples and comparison
def compare_algorithms():
    """Compare how different algorithms handle various scenarios"""

    scenarios = [
        {"desc": "New dev: 5 stars, 1 rating", "rating": 5.0, "count": 1},
        {"desc": "Growing dev: 4.8 stars, 10 ratings", "rating": 4.8, "count": 10},
        {"desc": "Established dev: 4.9 stars, 50 ratings", "rating": 4.9, "count": 50},
        {"desc": "Popular dev: 4.7 stars, 200 ratings", "rating": 4.7, "count": 200},
        {"desc": "Average dev: 3.5 stars, 30 ratings", "rating": 3.5, "count": 30},
        {"desc": "Poor dev: 2.0 stars, 15 ratings", "rating": 2.0, "count": 15},
    ]

    print("RYZE Score Comparison\n" + "=" * 80)
    print(f"{'Scenario':<35} {'Bayesian':<10} {'Weighted':<10} {'IMDB':<10}")
    print("-" * 80)

    for scenario in scenarios:
        bayesian = RyzeScoring.bayesian_average(scenario["rating"], scenario["count"])
        weighted = RyzeScoring.weighted_rating(scenario["rating"], scenario["count"])
        imdb = RyzeScoring.imdb_formula(scenario["rating"], scenario["count"])

        print(
            f"{scenario['desc']:<35} {bayesian:<10.2f} {weighted:<10.2f} {imdb:<10.2f}"
        )


# Example implementation for your database
def calculate_ryze_score_for_developer(developer_profile: Dict[str, Any]) -> float:
    """
    Calculate RYZE score for a developer profile
    Can be called when ratings change or periodically to update scores
    """
    average_rating = developer_profile.get("average_rating", 0)
    total_ratings = developer_profile.get("total_ratings", 0)

    # You can choose which algorithm works best for your platform
    # I recommend starting with Bayesian Average as it's most intuitive
    ryze_score = RyzeScoring.bayesian_average(average_rating, total_ratings)

    # Convert to percentage for display (multiply by 20 to get 0-100 scale)
    success_rate_percentage = min(ryze_score * 20, 100)

    return success_rate_percentage


if __name__ == "__main__":
    compare_algorithms()
