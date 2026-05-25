function SculptedPugBody({ frontLeft, frontRight, backLeft, backRight, tail, head, skinId, sk }) {
  const isDiamond = skinId === "diamond";
  const isMetal = sk.metalness >= 0.6;
  const isGlow = sk.emissiveIntensity > 0.3;

  // Derived accent colors. Brow is a slightly darker shade of the body
  // (10%); wrinkles are clearly darker (28%). We deliberately do NOT use
  // the `sheen` extension — without an IBL env map (we strip `<Environment>`
  // to avoid the Cloudflare-proxied HDR CloneError) sheen renders invalid
  // on most GPUs and the affected meshes drop out intermittently.
  const browColor = useMemo(() => shade(sk.body, 0.1), [sk.body]);
  const wrinkleColor = useMemo(() => shade(sk.body, 0.28), [sk.body]);
  const creaseColor = useMemo(() => shade(sk.dark, 0.4), [sk.dark]);

  // Adaptive material factory. Diamond branches into transmission for
  // body parts (we still allow per-call overrides for paws/jowls etc).
  const skin = (overrides = {}) => {
    if (isDiamond && !overrides.color) {
      return (
        <meshPhysicalMaterial
          color="#FFFFFF"
          emissive="#9DEAFF"
          emissiveIntensity={0.08}
          metalness={0.15}
          roughness={0.04}
          transmission={0.95}
          thickness={1.1}
          ior={2.4}
          attenuationColor="#BDF2FF"
          attenuationDistance={2.5}
          clearcoat={1}
          clearcoatRoughness={0.04}
          transparent
          opacity={0.95}
          envMapIntensity={1.4}
          {...overrides}
        />
      );
    }
    return (
      <meshPhysicalMaterial
        color={sk.body}
        emissive={sk.emissive}
        emissiveIntensity={sk.emissiveIntensity}
        metalness={sk.metalness}
        roughness={sk.roughness}
        clearcoat={isMetal ? 0.6 : 0.3}
        clearcoatRoughness={isMetal ? 0.15 : 0.5}
        envMapIntensity={isMetal ? 1.2 : 0.65}
        {...overrides}
      />
    );
  };

  // Tail curve — same 1.6-turn tightening spiral as Guardian.
  const tailCurve = useMemo(() => {
    const pts = [];
    const segs = 36;
    const turns = 1.6;
    for (let i = 0; i <= segs; i++) {
      const t = i / segs;
      const a = t * Math.PI * 2 * turns;
      const r = 0.085 - t * 0.045;
      const x = Math.sin(a) * r;
      const y = -Math.cos(a) * r + r;
      const z = t * 0.04;
      pts.push(new THREE.Vector3(x, y, z));
    }
    return new THREE.CatmullRomCurve3(pts);
  }, []);

  // Reusable leg with paw pad + 4 toe nubs. zSign flips toe position
  // forward/backward depending on whether this is a front or back leg.
  const Leg = ({ refLeg, x, z, zSign }) => (
    <group ref={refLeg} position={[x, 0.22, z]}>
      <mesh position={[0, -0.14, 0]}>
        <capsuleGeometry args={[0.14, 0.16, 16, 28]} />
        {skin()}
      </mesh>
      <mesh position={[0, -0.3, 0.03 * zSign]} scale={[1.25, 0.55, 1.45]}>
        <sphereGeometry args={[0.1, 24, 18]} />
        {skin({ color: sk.dark, roughness: 0.85, metalness: sk.metalness * 0.5 })}
      </mesh>
      {[-0.07, -0.024, 0.024, 0.07].map((tx, ti) => (
        <mesh key={ti} position={[tx, -0.32, 0.11 * zSign]}>
          <sphereGeometry args={[0.025, 14, 10]} />
          {skin({ color: sk.dark, roughness: 0.85, metalness: sk.metalness * 0.5 })}
        </mesh>
      ))}
    </group>
  );

  return (
    <>
      {/* ───── BODY — pear-shaped barrel ───── */}
      <mesh position={[0, 0.6, 0.22]} scale={[1.2, 1.08, 1.0]}>
        <sphereGeometry args={[0.46, 64, 48]} />
        {skin()}
      </mesh>
      <mesh position={[0, 0.5, 0]} scale={[1.05, 0.95, 1.0]}>
        <sphereGeometry args={[0.46, 64, 48]} />
        {skin()}
      </mesh>
      {/* Slim haunch (Iteration 154 tuning) */}
      <mesh position={[0, 0.6, -0.18]} scale={[0.82, 0.86, 0.78]}>
        <sphereGeometry args={[0.36, 48, 36]} />
        {skin()}
      </mesh>
      {/* Belly highlight — paler underside */}
      <mesh position={[0, 0.3, 0.08]} scale={[0.85, 0.42, 1.15]}>
        <sphereGeometry args={[0.46, 48, 32]} />
        {skin({ color: sk.belly })}
      </mesh>
      {/* Chest tuft */}
      <mesh position={[0, 0.52, 0.5]} scale={[0.65, 0.55, 0.35]}>
        <sphereGeometry args={[0.3, 32, 24]} />
        {skin({ color: sk.belly, roughness: Math.max(0.4, sk.roughness + 0.1) })}
      </mesh>
      {/* Shoulder blade bumps */}
      <mesh position={[-0.3, 0.78, 0.28]} scale={[0.75, 0.7, 0.75]}>
        <sphereGeometry args={[0.16, 28, 22]} />
        {skin({ roughness: Math.max(0.04, sk.roughness - 0.04) })}
      </mesh>
      <mesh position={[0.3, 0.78, 0.28]} scale={[0.75, 0.7, 0.75]}>
        <sphereGeometry args={[0.16, 28, 22]} />
        {skin({ roughness: Math.max(0.04, sk.roughness - 0.04) })}
      </mesh>

      {/* ───── HEAD ───── */}
      <group ref={head} position={[0, 1.08, 0.55]}>
        <mesh scale={[1.1, 0.95, 1.0]}>
          <sphereGeometry args={[0.4, 64, 48]} />
          {skin()}
        </mesh>
        {/* Cheek bulges */}
        <mesh position={[-0.3, -0.06, 0.1]} scale={[0.9, 0.95, 0.95]}>
          <sphereGeometry args={[0.18, 32, 24]} />
          {skin()}
        </mesh>
        <mesh position={[0.3, -0.06, 0.1]} scale={[0.9, 0.95, 0.95]}>
          <sphereGeometry args={[0.18, 32, 24]} />
          {skin()}
        </mesh>
        {/* Brow shelf */}
        <mesh position={[0, 0.16, 0.24]} scale={[1.15, 0.32, 0.7]}>
          <sphereGeometry args={[0.3, 32, 24]} />
          {skin({ color: browColor, roughness: Math.min(0.85, sk.roughness + 0.1) })}
        </mesh>
        {/* 3 brow wrinkles */}
        {[
          { y: 0.2, z: 0.34, sx: 0.78, sy: 0.05, sz: 0.1 },
          { y: 0.12, z: 0.37, sx: 0.82, sy: 0.045, sz: 0.09 },
          { y: 0.04, z: 0.39, sx: 0.72, sy: 0.04, sz: 0.08 },
        ].map((w, i) => (
          <mesh key={i} position={[0, w.y, w.z]} scale={[w.sx, w.sy, w.sz]}>
            <sphereGeometry args={[0.3, 24, 14]} />
            {skin({ color: wrinkleColor, roughness: Math.min(0.95, sk.roughness + 0.2) })}
          </mesh>
        ))}
        {/* Hanging jowls */}
        <mesh position={[-0.2, -0.24, 0.18]} scale={[0.85, 1.1, 1.05]}>
          <sphereGeometry args={[0.2, 36, 28]} />
          {skin()}
        </mesh>
        <mesh position={[0.2, -0.24, 0.18]} scale={[0.85, 1.1, 1.05]}>
          <sphereGeometry args={[0.2, 36, 28]} />
          {skin()}
        </mesh>
        {/* Pushed-in flat snout — uses sk.dark so each skin colors it differently */}
        <mesh position={[0, -0.1, 0.36]} scale={[1.15, 0.55, 0.55]}>
          <sphereGeometry args={[0.2, 36, 28]} />
          <meshPhysicalMaterial
            color={sk.dark}
            roughness={0.78}
            metalness={sk.metalness * 0.5}
            clearcoat={0.05}
          />
        </mesh>
        {/* Signature snout crease */}
        <mesh position={[0, -0.02, 0.44]} scale={[0.55, 0.07, 0.08]}>
          <sphereGeometry args={[0.2, 20, 14]} />
          <meshPhysicalMaterial color={creaseColor} roughness={0.85} />
        </mesh>
        {/* Wet nose pad — universal across skins */}
        <mesh position={[0, -0.05, 0.48]} scale={[1.15, 0.82, 0.55]}>
          <sphereGeometry args={[0.085, 32, 24]} />
          <meshPhysicalMaterial
            color="#0B0608"
            roughness={0.22}
            metalness={0.15}
            clearcoat={1.0}
            clearcoatRoughness={0.1}
          />
        </mesh>
        {/* Nostril dots */}
        <mesh position={[-0.028, -0.07, 0.525]}>
          <sphereGeometry args={[0.013, 12, 12]} />
          <meshBasicMaterial color="#000000" />
        </mesh>
        <mesh position={[0.028, -0.07, 0.525]}>
          <sphereGeometry args={[0.013, 12, 12]} />
          <meshBasicMaterial color="#000000" />
        </mesh>
        {/* Mouth crease */}
        <mesh position={[0, -0.24, 0.38]} rotation={[0.25, 0, 0]} scale={[0.5, 0.04, 0.04]}>
          <sphereGeometry args={[0.2, 16, 10]} />
          <meshBasicMaterial color={creaseColor} />
        </mesh>
        {/* Tongue tip — pink always (peeks through the mouth, skin-agnostic) */}
        <mesh position={[0, -0.27, 0.36]} scale={[0.26, 0.04, 0.18]}>
          <sphereGeometry args={[0.2, 16, 12]} />
          <meshStandardMaterial color="#D87A82" roughness={0.4} />
        </mesh>
        {/* Eyes — glow for emissive skins, deep-amber clearcoat otherwise */}
        <mesh position={[-0.16, 0.02, 0.34]}>
          <sphereGeometry args={[0.085, 32, 24]} />
          {isGlow ? (
            <meshStandardMaterial
              color="#0d0d12"
              emissive={sk.emissive}
              emissiveIntensity={Math.min(1.4, sk.emissiveIntensity * 1.2)}
              roughness={0.18}
              toneMapped={false}
            />
          ) : (
            <meshPhysicalMaterial color="#0B0508" roughness={0.16} clearcoat={1.0} clearcoatRoughness={0.05} />
          )}
        </mesh>
        <mesh position={[0.16, 0.02, 0.34]}>
          <sphereGeometry args={[0.085, 32, 24]} />
          {isGlow ? (
            <meshStandardMaterial
              color="#0d0d12"
              emissive={sk.emissive}
              emissiveIntensity={Math.min(1.4, sk.emissiveIntensity * 1.2)}
              roughness={0.18}
              toneMapped={false}
            />
          ) : (
            <meshPhysicalMaterial color="#0B0508" roughness={0.16} clearcoat={1.0} clearcoatRoughness={0.05} />
          )}
        </mesh>
        {/* Catch-light specks — non-glow skins only (glow eyes self-light) */}
        {!isGlow && (
          <>
            <mesh position={[-0.14, 0.05, 0.42]}>
              <sphereGeometry args={[0.024, 12, 12]} />
              <meshBasicMaterial color="#ffffff" />
            </mesh>
            <mesh position={[0.18, 0.05, 0.42]}>
              <sphereGeometry args={[0.024, 12, 12]} />
              <meshBasicMaterial color="#ffffff" />
            </mesh>
          </>
        )}
        {/* Floppy oversized ears */}
        <mesh position={[-0.34, 0.14, -0.02]} rotation={[0.3, -0.15, -0.55]} scale={[0.7, 1.45, 0.55]}>
          <sphereGeometry args={[0.16, 28, 22]} />
          <meshPhysicalMaterial
            color={sk.dark}
            roughness={0.82}
            metalness={sk.metalness * 0.6}
            clearcoat={0.1}
          />
        </mesh>
        <mesh position={[0.34, 0.14, -0.02]} rotation={[0.3, 0.15, 0.55]} scale={[0.7, 1.45, 0.55]}>
          <sphereGeometry args={[0.16, 28, 22]} />
          <meshPhysicalMaterial
            color={sk.dark}
            roughness={0.82}
            metalness={sk.metalness * 0.6}
            clearcoat={0.1}
          />
        </mesh>
        {/* HORNS — every pug wears them */}
        <Horn position={[-0.22, 0.36, 0.02]} mirror={-1} />
        <Horn position={[0.22, 0.36, 0.02]} mirror={1} />
        {/* Robot antenna — Cyber skin only */}
        {sk.extra === "robot" && (
          <mesh position={[0, 0.45, 0]}>
            <cylinderGeometry args={[0.015, 0.02, 0.32, 8]} />
            <meshStandardMaterial color="#9CA3AF" metalness={0.9} roughness={0.2} />
          </mesh>
        )}
      </group>

      {/* ───── LEGS ───── */}
      <Leg refLeg={frontLeft} x={-0.28} z={0.32} zSign={1} />
      <Leg refLeg={frontRight} x={0.28} z={0.32} zSign={1} />
      <Leg refLeg={backLeft} x={-0.26} z={-0.26} zSign={-1} />
      <Leg refLeg={backRight} x={0.26} z={-0.26} zSign={-1} />

      {/* ───── DOUBLE-CURL TAIL ───── */}
      <group ref={tail} position={[0, 0.85, -0.4]}>
        <mesh>
          <tubeGeometry args={[tailCurve, 64, 0.05, 12, false]} />
          {skin()}
        </mesh>
        {(() => {
          const tip = tailCurve.getPoint(1);
          return (
            <mesh position={[tip.x, tip.y, tip.z]}>
              <sphereGeometry args={[0.04, 18, 14]} />
              {skin()}
            </mesh>
          );
        })()}
      </group>
    </>
  );
}
