/**
 * HEALIO BESPOKE ENGINE - NEURAL FLOW v4.0
 * Cinematic Background Animation
 */

function initNeuralFlow() {
    const canvas = document.getElementById('bg-canvas-bespoke');
    if (!canvas) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const particlesCount = 3000;
    const positions = new Float32Array(particlesCount * 3);
    const sizes = new Float32Array(particlesCount);
    const opacities = new Float32Array(particlesCount);

    for (let i = 0; i < particlesCount; i++) {
        // Create organic spherical flow
        const radius = Math.random() * 5 + 2;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos((Math.random() * 2) - 1);

        positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = radius * Math.cos(phi);

        sizes[i] = Math.random() * 2;
        opacities[i] = Math.random();
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const material = new THREE.PointsMaterial({
        size: 0.015,
        color: '#3b82f6',
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    // Add glowing nucleus
    const sphereGeo = new THREE.SphereGeometry(2, 32, 32);
    const sphereMat = new THREE.MeshBasicMaterial({
        color: '#3b82f6',
        transparent: true,
        opacity: 0.05,
        wireframe: true
    });
    const nucleus = new THREE.Mesh(sphereGeo, sphereMat);
    scene.add(nucleus);

    camera.position.z = 8;

    // Movement Tracking
    let mouseX = 0;
    let mouseY = 0;
    document.addEventListener('mousemove', (e) => {
        mouseX = (e.clientX / window.innerWidth) - 0.5;
        mouseY = (e.clientY / window.innerHeight) - 0.5;
    });

    const clock = new THREE.Clock();

    const animate = () => {
        const elapsedTime = clock.getElapsedTime();
        requestAnimationFrame(animate);

        // Rhythmic organic movement
        particles.rotation.y = elapsedTime * 0.05;
        particles.rotation.x = mouseY * 0.2;
        particles.rotation.z = mouseX * 0.2;

        nucleus.rotation.y = -elapsedTime * 0.1;
        nucleus.scale.setScalar(1 + Math.sin(elapsedTime * 0.5) * 0.05);

        renderer.render(scene, camera);
    };

    animate();

    // Responsive
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

document.addEventListener('DOMContentLoaded', initNeuralFlow);

