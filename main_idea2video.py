import asyncio
import os
import argparse
from pipelines.idea2video_pipeline import Idea2VideoPipeline


def parse_args():
    parser = argparse.ArgumentParser(description='Generate video from idea')
    parser.add_argument('--idea', type=str,
                       default="A person doing yoga exercises in a peaceful studio.",
                       help='The core idea for the story')
    parser.add_argument('--requirement', type=str,
                       default="For adults, do not exceed 3 scenes. Each scene should be no more than 5 shots.",
                       help='User requirements for the story')
    parser.add_argument('--style', type=str, default="Cartoon style",
                       help='Visual style for images')
    parser.add_argument('--force', action='store_true',
                       help='Force regenerate all content (ignore cache)')
    parser.add_argument('--clean', action='store_true',
                       help='Clean working directory before starting')
    parser.add_argument('--seed', type=str, default=None,
                       help='Variation seed for prompt diversity (default: random)')
    return parser.parse_args()


async def main():
    args = parse_args()
    
    # Clean working directory if requested
    if args.clean:
        working_dir = ".working_dir/idea2video"
        if os.path.exists(working_dir):
            import shutil
            shutil.rmtree(working_dir)
            print(f"🧹 Cleaned working directory: {working_dir}")
    
    print("=" * 60)
    print("ViMax Idea2Video Pipeline")
    print("=" * 60)
    print(f"Idea: {args.idea}")
    print(f"Requirement: {args.requirement}")
    print(f"Style: {args.style}")
    print(f"Force Regenerate: {args.force}")
    print(f"Variation Seed: {args.seed if args.seed else 'random'}")
    print("=" * 60)
    
    pipeline = Idea2VideoPipeline.init_from_config(
        config_path="configs/idea2video.yaml")
    
    await pipeline(
        idea=args.idea,
        user_requirement=args.requirement,
        style=args.style,
        force_regenerate=args.force,
        variation_seed=args.seed,
    )

if __name__ == "__main__":
    asyncio.run(main())
