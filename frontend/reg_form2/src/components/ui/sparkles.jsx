import React, { useEffect, useState } from "react";
import Particles, { initParticlesEngine } from "@tsparticles/react";
import { loadSlim } from "@tsparticles/slim";

export const SparklesCore = (props) => {
  const {
    id,
    className,
    background,
    minSize,
    maxSize,
    speed,
    particleColor,
    particleDensity,
  } = props;

  const [init, setInit] = useState(false);

  useEffect(() => {
    initParticlesEngine(async (engine) => {
      await loadSlim(engine);
    }).then(() => {
      setInit(true);
    });
  }, []);

  const controls = {
    particles: {
      number: {
        value: particleDensity || 120,
        density: {
          enable: true,
          width: 800,
          height: 800,
        },
      },
      color: {
        value: particleColor || "#ffffff",
      },
      move: {
        enable: true,
        speed: speed || 2,
        direction: "none",
        random: false,
        straight: false,
        outModes: {
          default: "out",
        },
      },
      size: {
        value: { min: minSize || 1, max: maxSize || 3 },
      },
      opacity: {
        value: { min: 0.1, max: 1 },
        animation: {
          enable: true,
          speed: 1,
          sync: false,
        },
      },
    },
  };

  return (
    init && (
      <Particles
        id={id || "tsparticles"}
        className={className}
        options={{
          background: {
            color: {
              value: background || "#0d47a1",
            },
          },
          fullScreen: {
            enable: false,
            zIndex: 1,
          },
          fpsLimit: 120,
          interactivity: {
            events: {
              onClick: {
                enable: true,
                mode: "push",
              },
              onHover: {
                enable: false,
                mode: "repulse",
              },
              resize: true,
            },
            modes: {
              push: {
                quantity: 4,
              },
              repulse: {
                distance: 200,
                duration: 0.4,
              },
            },
          },
          particles: controls.particles,
          detectRetina: true,
        }}
      />
    )
  );
};