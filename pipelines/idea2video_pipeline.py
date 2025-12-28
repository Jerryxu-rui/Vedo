import os
import logging
from agents import Screenwriter, CharacterExtractor, CharacterPortraitsGenerator
from pipelines.script2video_pipeline import Script2VideoPipeline
from interfaces import CharacterInScene
from typing import List, Dict, Optional
import asyncio
import json
from moviepy import VideoFileClip, concatenate_videoclips
import yaml
from langchain.chat_models import init_chat_model
from utils.rate_limiter import RateLimiter
import importlib


class Idea2VideoPipeline:
    def __init__(
        self,
        chat_model: str,
        image_generator: str,
        video_generator: str,
        working_dir: str,
    ):
        self.chat_model = chat_model
        self.image_generator = image_generator
        self.video_generator = video_generator
        self.working_dir = working_dir
        os.makedirs(self.working_dir, exist_ok=True)

        self.screenwriter = Screenwriter(chat_model=self.chat_model)
        self.character_extractor = CharacterExtractor(
            chat_model=self.chat_model)
        self.character_portraits_generator = CharacterPortraitsGenerator(
            image_generator=self.image_generator)

    @classmethod
    def init_from_config(
        cls,
        config_path: str,
    ):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        chat_model_args = config["chat_model"]["init_args"]
        chat_model = init_chat_model(**chat_model_args)

        # Create separate rate limiters for each service
        chat_model_rpm = config.get("chat_model", {}).get("max_requests_per_minute", None)
        chat_model_rpd = config.get("chat_model", {}).get("max_requests_per_day", None)
        image_generator_rpm = config.get("image_generator", {}).get("max_requests_per_minute", None)
        image_generator_rpd = config.get("image_generator", {}).get("max_requests_per_day", None)
        video_generator_rpm = config.get("video_generator", {}).get("max_requests_per_minute", None)
        video_generator_rpd = config.get("video_generator", {}).get("max_requests_per_day", None)

        chat_model_rate_limiter = RateLimiter(
            max_requests_per_minute=chat_model_rpm,
            max_requests_per_day=chat_model_rpd
        ) if (chat_model_rpm or chat_model_rpd) else None

        image_rate_limiter = RateLimiter(
            max_requests_per_minute=image_generator_rpm,
            max_requests_per_day=image_generator_rpd
        ) if (image_generator_rpm or image_generator_rpd) else None

        video_rate_limiter = RateLimiter(
            max_requests_per_minute=video_generator_rpm,
            max_requests_per_day=video_generator_rpd
        ) if (video_generator_rpm or video_generator_rpd) else None

        # Display rate limiting configuration
        if chat_model_rate_limiter:
            limits = []
            if chat_model_rpm:
                limits.append(f"{chat_model_rpm} req/min")
            if chat_model_rpd:
                limits.append(f"{chat_model_rpd} req/day")
            print(f"Chat model rate limiting: {', '.join(limits)}")

        if image_rate_limiter:
            limits = []
            if image_generator_rpm:
                limits.append(f"{image_generator_rpm} req/min")
            if image_generator_rpd:
                limits.append(f"{image_generator_rpd} req/day")
            print(f"Image generator rate limiting: {', '.join(limits)}")

        if video_rate_limiter:
            limits = []
            if video_generator_rpm:
                limits.append(f"{video_generator_rpm} req/min")
            if video_generator_rpd:
                limits.append(f"{video_generator_rpd} req/day")
            print(f"Video generator rate limiting: {', '.join(limits)}")

        image_generator_cls_module, image_generator_cls_name = config["image_generator"]["class_path"].rsplit(
            ".", 1)
        image_generator_cls = getattr(importlib.import_module(
            image_generator_cls_module), image_generator_cls_name)
        image_generator_args = config["image_generator"]["init_args"]
        image_generator_args["rate_limiter"] = image_rate_limiter
        image_generator = image_generator_cls(**image_generator_args)

        video_generator_cls_module, video_generator_cls_name = config["video_generator"]["class_path"].rsplit(
            ".", 1)
        video_generator_cls = getattr(importlib.import_module(
            video_generator_cls_module), video_generator_cls_name)
        video_generator_args = config["video_generator"]["init_args"]
        video_generator_args["rate_limiter"] = video_rate_limiter
        video_generator = video_generator_cls(**video_generator_args)

        return cls(
            chat_model=chat_model,
            image_generator=image_generator,
            video_generator=video_generator,
            working_dir=config["working_dir"],
        )

    async def extract_characters(
        self,
        story: str,
        force_regenerate: bool = False,
    ):
        # Create a hash of the story to use as cache key
        import hashlib
        story_hash = hashlib.md5(story.encode()).hexdigest()[:8]
        save_path = os.path.join(self.working_dir, f"characters_{story_hash}.json")

        if os.path.exists(save_path) and not force_regenerate:
            with open(save_path, "r", encoding="utf-8") as f:
                characters = json.load(f)
            characters = [CharacterInScene.model_validate(
                character) for character in characters]
            print(f"🚀 Loaded {len(characters)} characters from cache (hash: {story_hash}).")
        else:
            characters = await self.character_extractor.extract_characters(story)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump([character.model_dump()
                          for character in characters], f, ensure_ascii=False, indent=4)
            print(
                f"✅ Extracted {len(characters)} characters from story and saved to {save_path} (hash: {story_hash}).")

        return characters

    async def generate_character_portraits(
        self,
        characters: List[CharacterInScene],
        character_portraits_registry: Optional[Dict[str, Dict[str, Dict[str, str]]]],
        style: str,
        force_regenerate: bool = False,
    ):
        character_portraits_registry_path = os.path.join(
            self.working_dir, "character_portraits_registry.json")
        
        # Clear registry and portrait files if force regeneration is requested
        if force_regenerate:
            print("🧹 Force regenerating character portraits...")
            character_portraits_registry = {}
            # Clear registry file
            if os.path.exists(character_portraits_registry_path):
                os.remove(character_portraits_registry_path)
            # Clear character portraits directory
            character_portraits_dir = os.path.join(self.working_dir, "character_portraits")
            if os.path.exists(character_portraits_dir):
                import shutil
                shutil.rmtree(character_portraits_dir)
                print(f"🧹 Cleared character portraits directory: {character_portraits_dir}")
        
        if character_portraits_registry is None:
            if os.path.exists(character_portraits_registry_path):
                with open(character_portraits_registry_path, 'r', encoding='utf-8') as f:
                    character_portraits_registry = json.load(f)
            else:
                character_portraits_registry = {}

        # Debug logging
        print(f"🔍 Character portrait registry has {len(character_portraits_registry)} entries")
        print(f"🔍 Characters to process: {[c.identifier_in_scene for c in characters]}")
        
        tasks = [
            self.generate_portraits_for_single_character(character, style)
            for character in characters
            if character.identifier_in_scene not in character_portraits_registry
        ]
        
        print(f"🔍 Tasks to execute: {len(tasks)} character portraits to generate")
        
        if tasks:
            for future in asyncio.as_completed(tasks):
                character_portraits_registry.update(await future)
                with open(character_portraits_registry_path, 'w', encoding='utf-8') as f:
                    json.dump(character_portraits_registry,
                              f, ensure_ascii=False, indent=4)

            print(
                f"✅ Completed character portrait generation for {len(tasks)} characters.")
        else:
            print(
                "🚀 All characters already have portraits, skipping portrait generation.")

        return character_portraits_registry

    async def develop_story(
        self,
        idea: str,
        user_requirement: str,
        force_regenerate: bool = False,
        variation_seed: Optional[str] = None,
    ):
        # Create a hash of inputs to use as cache key, include variation seed for diversity
        import hashlib
        import time
        import random
        
        # Use variation seed if provided, otherwise generate one based on timestamp
        if variation_seed is None:
            variation_seed = str(time.time())[-6:] + str(random.randint(0, 9999)).zfill(4)
        
        cache_key = f"{idea}_{user_requirement}_{variation_seed}"
        input_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]  # Longer hash for more uniqueness
        save_path = os.path.join(self.working_dir, f"story_{input_hash}.txt")
        
        if os.path.exists(save_path) and not force_regenerate:
            with open(save_path, "r", encoding="utf-8") as f:
                story = f.read()
            print(f"🚀 Loaded story from cache (hash: {input_hash}, seed: {variation_seed}).")
        else:
            print(f"🧠 Developing story with variation seed: {variation_seed}...")
            story = await self.screenwriter.develop_story(idea=idea, user_requirement=user_requirement)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(story)
            print(f"✅ Developed story and saved to {save_path} (hash: {input_hash}, seed: {variation_seed}).")

        return story

    async def write_script_based_on_story(
        self,
        story: str,
        user_requirement: str,
        force_regenerate: bool = False,
        variation_seed: Optional[str] = None,
    ):
        # Create a hash of inputs to use as cache key, include variation seed for diversity
        import hashlib
        import time
        import random
        
        # Use variation seed if provided, otherwise generate one based on timestamp
        if variation_seed is None:
            variation_seed = str(time.time())[-6:] + str(random.randint(0, 9999)).zfill(4)
        
        cache_key = f"{story}_{user_requirement}_{variation_seed}"
        input_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]
        save_path = os.path.join(self.working_dir, f"script_{input_hash}.json")
        
        if os.path.exists(save_path) and not force_regenerate:
            with open(save_path, "r", encoding="utf-8") as f:
                script = json.load(f)
            print(f"🚀 Loaded script from cache (hash: {input_hash}, seed: {variation_seed}).")
        else:
            print(f"🧠 Writing script based on story with variation seed: {variation_seed}...")
            script = await self.screenwriter.write_script_based_on_story(story=story, user_requirement=user_requirement)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=4)
            print(f"✅ Written script based on story and saved to {save_path} (hash: {input_hash}, seed: {variation_seed}).")
        return script

    async def generate_portraits_for_single_character(
        self,
        character: CharacterInScene,
        style: str,
    ):
        character_dir = os.path.join(
            self.working_dir, "character_portraits", f"{character.idx}_{character.identifier_in_scene}")
        os.makedirs(character_dir, exist_ok=True)

        front_portrait_path = os.path.join(character_dir, "front.png")
        if os.path.exists(front_portrait_path):
            pass
        else:
            front_portrait_output = await self.character_portraits_generator.generate_front_portrait(character, style)
            front_portrait_output.save(front_portrait_path)

        side_portrait_path = os.path.join(character_dir, "side.png")
        if os.path.exists(side_portrait_path):
            pass
        else:
            side_portrait_output = await self.character_portraits_generator.generate_side_portrait(character, front_portrait_path)
            side_portrait_output.save(side_portrait_path)

        back_portrait_path = os.path.join(character_dir, "back.png")
        if os.path.exists(back_portrait_path):
            pass
        else:
            back_portrait_output = await self.character_portraits_generator.generate_back_portrait(character, front_portrait_path)
            back_portrait_output.save(back_portrait_path)

        print(
            f"☑️ Completed character portrait generation for {character.identifier_in_scene}.")

        return {
            character.identifier_in_scene: {
                "front": {
                    "path": front_portrait_path,
                    "description": f"A front view portrait of {character.identifier_in_scene}.",
                },
                "side": {
                    "path": side_portrait_path,
                    "description": f"A side view portrait of {character.identifier_in_scene}.",
                },
                "back": {
                    "path": back_portrait_path,
                    "description": f"A back view portrait of {character.identifier_in_scene}.",
                },
            }
        }

    async def __call__(
        self,
        idea: str,
        user_requirement: str,
        style: str,
        force_regenerate: bool = False,
        variation_seed: Optional[str] = None,
    ):
        import time
        import random
        
        # Generate variation seed if not provided
        if variation_seed is None:
            variation_seed = str(time.time())[-8:] + str(random.randint(0, 99999)).zfill(5)
            print(f"🎲 Using variation seed: {variation_seed} for prompt diversity")

        story = await self.develop_story(
            idea=idea,
            user_requirement=user_requirement,
            force_regenerate=force_regenerate,
            variation_seed=variation_seed,
        )

        characters = await self.extract_characters(
            story=story,
            force_regenerate=force_regenerate
        )

        character_portraits_registry = await self.generate_character_portraits(
            characters=characters,
            character_portraits_registry=None,
            style=style,
            force_regenerate=force_regenerate,
        )

        scene_scripts = await self.write_script_based_on_story(
            story=story,
            user_requirement=user_requirement,
            force_regenerate=force_regenerate,
            variation_seed=variation_seed,
        )

        all_video_paths = []

        for idx, scene_script in enumerate(scene_scripts):
            scene_working_dir = os.path.join(self.working_dir, f"scene_{idx}")
            os.makedirs(scene_working_dir, exist_ok=True)
            script2video_pipeline = Script2VideoPipeline(
                chat_model=self.chat_model,
                image_generator=self.image_generator,
                video_generator=self.video_generator,
                working_dir=scene_working_dir,
            )
            final_video_path = await script2video_pipeline(
                script=scene_script,
                user_requirement=user_requirement,
                style=style,
                characters=characters,
                character_portraits_registry=character_portraits_registry,
            )
            all_video_paths.append(final_video_path)

        final_video_path = os.path.join(self.working_dir, "final_video.mp4")
        if os.path.exists(final_video_path):
            print(f"🚀 Skipped concatenating videos, already exists.")
        else:
            print(f"🎬 Starting concatenating videos...")
            video_clips = [VideoFileClip(final_video_path)
                           for final_video_path in all_video_paths]
            final_video = concatenate_videoclips(video_clips)
            final_video.write_videofile(final_video_path)
            print(f"☑️ Concatenated videos, saved to {final_video_path}.")
        return final_video_path
