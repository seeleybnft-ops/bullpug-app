import { Canvas } from "@react-three/fiber";
import { Stars, Sparkles, Environment } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { BlendFunction, KernelSize } from "postprocessing";
import * as THREE from "three";
import { Bullpug } from "@/pages/Phase1Runner3D";

/**
 * Compact 3D preview of an equipped pug skin — used inside the SkinStore
 * "Current Selection" card so players can see flames flicker, gold ring
 * spin, halo rotate etc. before they swap into a run.
 *
 * Re-uses the live game's Bullpug component in `idle` mode (no x/y refs,
 * no jump/slide animation, just a slow auto-rotate + bob), and the same
 * SkinExtras VFX layer rendered inline via Bullpug's render path.
 */
export default function SkinPreview3D({ skinId, size = 160, glowColor = "#D946EF" }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: 16,
        overflow: "hidden",
        background: "linear-gradient(180deg, #0b0820 0%, #1a0942 100%)",
        boxShadow: `inset 0 0 40px ${glowColor}30, 0 0 20px ${glowColor}25`,
      }}
      data-testid={`skin-preview-3d-${skinId}`}
    >
      <Canvas
        camera={{ position: [0, 1.4, 3.0], fov: 38 }}
        dpr={[1, 1.6]}
        gl={{
          antialias: true,
          powerPreference: "high-performance",
          toneMapping: THREE.ACESFilmicToneMapping,
          outputColorSpace: THREE.SRGBColorSpace,
        }}
        onCreated={({ gl }) => {
          gl.toneMappingExposure = 1.2;
        }}
      >
        <hemisphereLight args={["#5b3a8a", "#0b0820", 0.6]} />
        <ambientLight intensity={0.35} />
        <Environment preset="city" background={false} environmentIntensity={0.8} />
        <directionalLight position={[3, 5, 3]} intensity={1.0} color="#fff5d6" />
        <directionalLight position={[-3, 2, -3]} intensity={0.7} color="#D946EF" />
        <pointLight position={[0, 2, 1.5]} intensity={0.5} color="#00FFA3" />

        <Stars radius={20} depth={20} count={400} factor={2.5} fade saturation={0.7} />
        <Sparkles count={40} scale={[3.5, 2.5, 3.5]} size={2.0} speed={0.3} color={glowColor} />

        {/* Pug — idle preview mode with slow auto-rotate, plus SkinExtras VFX layer */}
        <group position={[0, -0.4, 0]}>
          <Bullpug skinId={skinId} idle />
        </group>

        {/* Soft pedestal disc to ground the pug visually */}
        <mesh position={[0, -0.42, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.55, 0.95, 32]} />
          <meshBasicMaterial color={glowColor} transparent opacity={0.18} toneMapped={false} />
        </mesh>

        <EffectComposer multisampling={0} disableNormalPass>
          <Bloom
            intensity={1.1}
            luminanceThreshold={0.22}
            luminanceSmoothing={0.65}
            mipmapBlur
            kernelSize={KernelSize.LARGE}
            blendFunction={BlendFunction.SCREEN}
          />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
