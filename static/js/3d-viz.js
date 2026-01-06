document.addEventListener("DOMContentLoaded", function() {
    const container = document.getElementById('three-container');
    if(!container) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc);
    
    // Camera
    const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(15, 10, 20);
    camera.lookAt(0, 0, 0);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    // Grid
    const gridHelper = new THREE.GridHelper(30, 20, 0xcbd5e1, 0xe2e8f0);
    scene.add(gridHelper);

    // Function to create animated 3D lines
    function createLine(color, zOffset, speed, amp) {
        const points = [];
        const segments = 100;
        for (let i = 0; i < segments; i++) {
            points.push(new THREE.Vector3((i - segments/2)*0.4, 0, zOffset));
        }
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({ color: color, linewidth: 3 });
        const line = new THREE.Line(geometry, material);
        line.userData = { speed: speed, amp: amp, timeOffset: Math.random() * 100 };
        scene.add(line);
        return line;
    }

    const lineHR = createLine(0xef4444, 4, 2.5, 2); // Red
    const lineSpO2 = createLine(0x3b82f6, 0, 1.5, 1.5); // Blue
    const lineBP = createLine(0x0d9488, -4, 2.0, 1); // Teal

    // Animation Loop
    function animate() {
        requestAnimationFrame(animate);
        const time = Date.now() * 0.001;

        [lineHR, lineSpO2, lineBP].forEach(line => {
            const positions = line.geometry.attributes.position;
            const amp = line.userData.amp;
            const speed = line.userData.speed;
            
            for(let i=0; i < positions.count; i++) {
                const x = positions.getX(i);
                // Create wave movement
                const y = Math.sin(x * 0.5 + time * speed + line.userData.timeOffset) * amp;
                
                // Add "anomaly" spike effect occasionally
                let spike = 0;
                if(line === lineHR && Math.abs(x - Math.sin(time)*5) < 1) spike = 2;
                
                positions.setY(i, y + spike + (line===lineHR?3:line===lineBP?-3:0));
            }
            positions.needsUpdate = true;
        });

        renderer.render(scene, camera);
    }
    animate();

    // Resize handler
    window.addEventListener('resize', () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });
});